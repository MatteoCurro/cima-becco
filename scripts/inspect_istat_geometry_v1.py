#!/usr/bin/env python3
"""Audit-only: official ISTAT 2021 località point shapefile layout before mapping."""
import io, json, struct, sys, zipfile
from pathlib import Path
p=Path(sys.argv[1])
with zipfile.ZipFile(p) as z:
    files=z.infolist()
    print('ARCHIVE',p.name,'compressed_bytes',p.stat().st_size,'members',len(files))
    for entry in files[:60]:
        print('ZIP MEMBER',entry.filename,'size',entry.file_size)
    for entry in files:
        if not entry.filename.lower().endswith('.dbf'): continue
        raw=z.read(entry)
        if len(raw)<64:continue
        rows=struct.unpack_from('<I',raw,4)[0]
        headerlen=struct.unpack_from('<H',raw,8)[0]
        recordlen=struct.unpack_from('<H',raw,10)[0]
        print('DBF',entry.filename,'rows',rows,'header',headerlen,'record',recordlen)
        fields=[];pos=32
        while pos+32<=headerlen and raw[pos]!=0x0d:
            f=raw[pos:pos+32]
            name=f[:11].split(b'\0')[0].decode('latin1','replace')
            fields.append((name,chr(f[11]),f[16]))
            pos+=32
        print('FIELDS',json.dumps(fields))
        for rowidx in range(min(rows,3)):
            rec=raw[headerlen+rowidx*recordlen:headerlen+(rowidx+1)*recordlen]
            off=1;sample={}
            for name,ty,width in fields:
                sample[name]=rec[off:off+width].decode('utf-8','replace').strip()
                off+=width
            print('ROW',rowidx,json.dumps(sample,ensure_ascii=False))
    for entry in files:
        if entry.filename.lower().endswith('.prj'):
            print('CRS',entry.filename,z.read(entry)[:1500].decode('utf-8','replace'))
