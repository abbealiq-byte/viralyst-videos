"""Viralyst channel scanner (YouTube Data API v3, free quota).
Each file in scans/requests/<name>.txt holds one channel reference:
@handle, channel URL, channel ID (UC...), or any video URL from the channel.
Writes scans/results/<name>.json and scans/results/<name>.md.
"""
import os, re, json, sys, glob, statistics, datetime as dt, urllib.request, urllib.parse

KEY = os.environ.get('YOUTUBE_API_KEY')
API = 'https://www.googleapis.com/youtube/v3/'
MAX_VIDEOS = int(os.environ.get('SCAN_MAX_VIDEOS', '500'))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
units = 0

def get(endpoint, **params):
    global units
    params['key'] = KEY
    url = API + endpoint + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        units += 1
        return json.load(r)

def iso_dur(s):
    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or '')
    if not m: return 0
    d, h, mi, se = (int(x) if x else 0 for x in m.groups())
    return d*86400 + h*3600 + mi*60 + se

def resolve(ref):
    ref = ref.strip()
    v = re.search(r'(?:v=|youtu\.be/|/shorts/|/live/)([A-Za-z0-9_-]{11})', ref)
    if v:
        it = get('videos', part='snippet', id=v.group(1))['items']
        return it[0]['snippet']['channelId'] if it else None
    c = re.search(r'(UC[A-Za-z0-9_-]{22})', ref)
    if c: return c.group(1)
    h = re.search(r'@([A-Za-z0-9._-]+)', ref)
    handle = h.group(1) if h else ref.rstrip('/').split('/')[-1]
    it = get('channels', part='id', forHandle='@' + handle).get('items', [])
    if it: return it[0]['id']
    it = get('search', part='snippet', type='channel', q=handle, maxResults=1).get('items', [])
    return it[0]['snippet']['channelId'] if it else None

def comments(video_id, n=15):
    try:
        r = get('commentThreads', part='snippet', videoId=video_id, order='relevance', maxResults=n, textFormat='plainText')
        return [{'text': i['snippet']['topLevelComment']['snippet']['textDisplay'][:300],
                 'likes': i['snippet']['topLevelComment']['snippet']['likeCount']} for i in r.get('items', [])]
    except Exception as e:
        return [{'error': str(e)[:120]}]

def transcript(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        try:
            fetched = YouTubeTranscriptApi().fetch(video_id, languages=['en', 'sv'])
            parts = [s.text for s in fetched]
        except AttributeError:
            parts = [s['text'] for s in YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'sv'])]
        return ' '.join(parts)[:4000]
    except Exception as e:
        return None

def scan(ref):
    cid = resolve(ref)
    if not cid: raise SystemExit(f'Could not resolve channel: {ref}')
    ch = get('channels', part='snippet,statistics,contentDetails,brandingSettings', id=cid)['items'][0]
    uploads = ch['contentDetails']['relatedPlaylists']['uploads']
    ids, token = [], None
    while len(ids) < MAX_VIDEOS:
        p = dict(part='contentDetails', playlistId=uploads, maxResults=50)
        if token: p['pageToken'] = token
        r = get('playlistItems', **p)
        ids += [i['contentDetails']['videoId'] for i in r.get('items', [])]
        token = r.get('nextPageToken')
        if not token: break
    vids = []
    now = dt.datetime.now(dt.timezone.utc)
    for i in range(0, len(ids), 50):
        r = get('videos', part='snippet,statistics,contentDetails', id=','.join(ids[i:i+50]))
        for v in r.get('items', []):
            s, st = v['snippet'], v.get('statistics', {})
            pub = dt.datetime.fromisoformat(s['publishedAt'].replace('Z', '+00:00'))
            views = int(st.get('viewCount', 0)); dur = iso_dur(v['contentDetails'].get('duration'))
            vids.append({'id': v['id'], 'title': s['title'], 'published': s['publishedAt'],
                'weekday_utc': pub.strftime('%a'), 'hour_utc': pub.hour,
                'age_days': max(1, (now - pub).days), 'duration_s': dur, 'short': dur <= 180,
                'views': views, 'likes': int(st.get('likeCount', 0)), 'comments': int(st.get('commentCount', 0)),
                'tags': s.get('tags', [])[:15], 'description': s.get('description', '')[:400]})
    vids.sort(key=lambda x: x['published'], reverse=True)
    med = statistics.median([v['views'] for v in vids]) if vids else 0
    for v in vids:
        v['views_per_day'] = round(v['views'] / v['age_days'], 1)
        v['vs_median'] = round(v['views'] / med, 2) if med else None
        v['like_rate_pct'] = round(100 * v['likes'] / v['views'], 2) if v['views'] else 0
    recent = vids[:50]
    rmed = statistics.median([v['views'] for v in recent]) if recent else 0
    for v in recent: v['vs_recent_median'] = round(v['views'] / rmed, 2) if rmed else None
    top = sorted(vids, key=lambda x: x['views'], reverse=True)[:10]
    outliers = sorted(recent, key=lambda x: x['vs_recent_median'] or 0, reverse=True)[:5]
    for v in outliers:
        v['top_comments'] = comments(v['id'])
        v['transcript'] = transcript(v['id'])
    def dist(key):
        d = {}
        for v in vids: d[str(v[key])] = d.get(str(v[key]), 0) + 1
        return d
    def group(f):
        g = [v for v in vids if f(v)]
        return {'count': len(g), 'median_views': statistics.median([v['views'] for v in g]) if g else 0}
    out = {'scanned_at': now.isoformat(), 'request': ref, 'quota_units_used': None,
        'channel': {'id': cid, 'title': ch['snippet']['title'], 'handle': ch['snippet'].get('customUrl'),
            'created': ch['snippet']['publishedAt'], 'country': ch['snippet'].get('country'),
            'description': ch['snippet'].get('description', '')[:600],
            'subscribers': int(ch['statistics'].get('subscriberCount', 0)),
            'total_views': int(ch['statistics'].get('viewCount', 0)),
            'video_count': int(ch['statistics'].get('videoCount', 0))},
        'summary': {'videos_scanned': len(vids), 'median_views_all': med, 'median_views_recent50': rmed,
            'shorts': group(lambda v: v['short']), 'long_form': group(lambda v: not v['short']),
            'uploads_last_30_days': sum(1 for v in vids if v['age_days'] <= 30),
            'publish_weekday_utc': dist('weekday_utc'), 'publish_hour_utc': dist('hour_utc')},
        'top10_all_time': top, 'top5_recent_outliers': outliers, 'videos': vids}
    out['quota_units_used'] = units
    return out

def md(r):
    c, s = r['channel'], r['summary']
    L = [f"# {c['title']} ({c['handle']})", '',
         f"Subscribers {c['subscribers']:,} | total views {c['total_views']:,} | videos {c['video_count']:,} | created {c['created'][:10]}",
         f"Scanned {s['videos_scanned']} videos | median views {s['median_views_all']:,.0f} (recent 50: {s['median_views_recent50']:,.0f})",
         f"Shorts: {s['shorts']['count']} (median {s['shorts']['median_views']:,.0f}) | long: {s['long_form']['count']} (median {s['long_form']['median_views']:,.0f}) | last 30 days: {s['uploads_last_30_days']} uploads", '',
         '## Top 10 all time']
    for v in r['top10_all_time']:
        L.append(f"- {v['views']:,} views | {v['duration_s']}s | {v['published'][:10]} | {v['title']}")
    L += ['', '## Top recent outliers (vs median of last 50)']
    for v in r['top5_recent_outliers']:
        L.append(f"- x{v['vs_recent_median']} | {v['views']:,} views | {v['title']} | transcript: {'yes' if v.get('transcript') else 'no'}")
    return '\n'.join(L) + '\n'

if __name__ == '__main__':
    if not KEY: raise SystemExit('YOUTUBE_API_KEY missing')
    done = 0
    for req in sorted(glob.glob(os.path.join(ROOT, 'scans', 'requests', '*.txt'))):
        name = os.path.splitext(os.path.basename(req))[0]
        out = os.path.join(ROOT, 'scans', 'results', name + '.json')
        if os.path.exists(out): continue
        units = 0
        r = scan(open(req).read().strip())
        json.dump(r, open(out, 'w'), indent=1, ensure_ascii=False)
        open(out[:-5] + '.md', 'w').write(md(r))
        print(f"scanned {name}: {r['channel']['title']} ({r['summary']['videos_scanned']} videos, {r['quota_units_used']} units)")
        done += 1
    print(f'{done} scan(s)')
