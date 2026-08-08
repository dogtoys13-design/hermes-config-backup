import urllib.request, ssl, sys, io, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://www.xiaohongshu.com/discovery/item/6a69e3e6000000000e03f400?app_platform=ios&app_version=9.41.2&share_from_user_hidden=true&xsec_source=app_share&type=normal&xsec_token=CBVjYk6_C6eN_S4Lpzgc-3VGibi9gQto2DBLYalyU0Ue8=&author_share=1&xhsshare=CopyLink&shareRedId=ODg1RDVLNEI2NzUyOTgwNjg0OTlFOjhO&apptime=1786172556&share_id=373b1ea6c4824eaa96a8ec0977545977'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1',
    'Accept-Language': 'zh-CN,zh;q=0.9',
})
resp = urllib.request.urlopen(req, timeout=20, context=ctx)
html = resp.read().decode('utf-8', errors='replace')

imgs = re.findall(r'https?://sns-webpic[^"\']*?xhscdn\.com[^"\']*?(?:jpg|jpeg|png|webp)', html)
imgs = [i.replace('\\u002F', '/') for i in imgs]
seen = set()
uniq = []
for i in imgs:
    if i not in seen and '!h5_1080' in i:
        seen.add(i)
        uniq.append(i)

outdir = r'C:\Vault\_待审核\xhs_六种方法'
os.makedirs(outdir, exist_ok=True)
print('downloading', len(uniq), 'images...')
for idx, u in enumerate(uniq):
    u = 'https://' + u if u.startswith('sns') else u
    fname = os.path.join(outdir, f'xhs_{idx+1}.jpg')
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30, context=ctx)
        data = r.read()
        with open(fname, 'wb') as f:
            f.write(data)
        print(f'img{idx+1}: {len(data)} bytes -> {fname}')
    except Exception as e:
        print(f'img{idx+1} ERR: {e}')
