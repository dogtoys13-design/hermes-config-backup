"""解密Chrome cookies获取抖音 s_v_web_id / ttwid（Windows DPAPI + AES-GCM）"""
import sys, io, os, json, base64, ctypes, ctypes.wintypes, sqlite3, shutil, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 1. 读取 Local State 拿加密key
local_state_path = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Local State')
if not os.path.exists(local_state_path):
    print('Local State 不存在')
    sys.exit(1)
with open(local_state_path, encoding='utf-8') as f:
    ls = json.load(f)
enc_key = base64.b64decode(ls['os_crypt']['encrypted_key'])
# 去掉 'DPAPI' 前缀
assert enc_key[:5] == b'DPAPI'
enc_key = enc_key[5:]

# 2. DPAPI 解密 key
class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

def dpapi_decrypt(blob_in):
    blob_out = DATA_BLOB()
    blob_in_data = DATA_BLOB(len(blob_in), ctypes.cast(ctypes.create_string_buffer(blob_in), ctypes.POINTER(ctypes.c_char)))
    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in_data), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError()
    data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return data

try:
    key = dpapi_decrypt(enc_key)
    print('DPAPI解密key成功, len:', len(key))
except Exception as e:
    print('DPAPI失败:', e)
    sys.exit(1)

# 3. 读 cookies 数据库（复制避免锁）—— 先试Chrome再试Edge
cookie_paths = [
    os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies'),
    os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Network\Cookies'),
]
cookie_db = None
for p in cookie_paths:
    if os.path.exists(p):
        cookie_db = p
        print('使用浏览器cookies:', p)
        break
if not cookie_db:
    print('无浏览器cookies数据库')
    sys.exit(1)
tmp = os.path.join(tempfile.gettempdir(), 'chrome_cookies_tmp.db')
shutil.copy2(cookie_db, tmp)
conn = sqlite3.connect(tmp)
rows = conn.execute("SELECT host_key, name, value, encrypted_value FROM cookies WHERE host_key LIKE '%douyin%' OR host_key LIKE '%iesdouyin%'").fetchall()
print('抖音相关cookie数:', len(rows))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
for host, name, value, enc in rows:
    if value:
        print(f'{host} | {name} = {value[:60]}')
        continue
    if not enc or enc[:3] != b'v10':
        continue
    try:
        nonce = enc[3:15]
        ciphertext = enc[15:]
        plain = AESGCM(key).decrypt(nonce, ciphertext, None)
        print(f'{host} | {name} = {plain.decode()[:80]}')
    except Exception as e:
        print(f'{host} | {name} = 解密失败: {e}')

conn.close()
os.remove(tmp)
