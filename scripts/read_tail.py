import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
with open(r'C:\Vault\Raw（原始资料）\投资\投资理念\待审-2026-09-04-全哥-douyin_7681475988240.md', encoding='utf-8') as f:
    content = f.read()
idx = content.find('**📝 全文')
text = content[idx:]
print('total len:', len(text))
# 输出2000-2900范围
seg = text[2000:2900]
print(seg)
