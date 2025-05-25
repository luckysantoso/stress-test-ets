import os
import json
import base64
from glob import glob
import logging
import hashlib
import shutil
import zlib
logging.basicConfig(level=logging.ERROR)
def detect_file_type(file_bytes):
    header = file_bytes[:16]  # read enough bytes

    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    elif header.startswith(b'\xff\xd8\xff'):
        return '.jpeg'
    elif header.startswith(b'%PDF'):
        return '.pdf'
    elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
        return '.gif'
    elif header.startswith(b'PK\x03\x04'):
        return '.zip'
    elif header.startswith(b'ID3') or header[:2] == b'\xff\xfb':
        return '.mpeg'
    else:
        return ''  # fallback for unknown

class FileInterface:
    def __init__(self):
        os.chdir('files/')

    def list(self,params=[]):
        try:
            filelist = glob('*.*')
            return dict(status='OK',data=filelist)
        except Exception as e:
            return dict(status='ERROR',data=str(e))

    def get(self,params=[]):
        try:
            filename = params[0]
            if (filename == ''):
                return None
            fp = open(f"{filename}",'rb')
            isifile = base64.b64encode(fp.read()).decode()
            return dict(status='OK',data_namafile=filename,data_file=isifile)
        except Exception as e:
            return dict(status='ERROR',data=str(e))
        
    def upload(self, params=[]):
        try:
            temp_filepath = params[0]

            with open(temp_filepath, 'rb') as f:
                file_bytes = f.read()
                hashed_name = hashlib.md5(file_bytes).hexdigest() 
                file_type = detect_file_type(file_bytes)

            with open(hashed_name+file_type, 'wb') as out_f:
                out_f.write(file_bytes)

            return dict(
                status='OK',
                message='File uploaded successfully',
                data=dict(
                    file_path=hashed_name+file_type,
                )
            )
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def delete(self, params=[]):
        try:
            filename = params[0]
            if (filename == ''):
                return None
            os.remove(filename)
            return dict(status='OK', message='File deleted successfully')
        except Exception as e:
            return dict(status='ERROR', data=str(e))

if __name__=='__main__':
    f = FileInterface()
    print(f.list())
    print(f.get(['pokijan.jpg']))