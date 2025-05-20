## Cara Menjalankan

### 1. Jalankan Server

Buka terminal pertama, lalu jalankan:

```bash
python file_server.py
```

Server akan aktif di port 6666.

### 2. Jalankan Client

Buka terminal kedua, jalankan:

```bash
python file_client_cli.py
```

Akan muncul menu seperti ini:

```
Command List:

1: LIST
2: GET <NAMAFILE>
3: UPLOAD <NAMAFILE>
4: DELETE <NAMAFILE>
5: EXIT
```

---

## Contoh Penggunaan

- Menampilkan daftar file:

  ```
  LIST
  ```

- Mengambil file dari server:

  ```
  GET PROTOKOL.txt
  ```

- Mengirim file ke server:

  ```
  UPLOAD PROTOKOL.txt
  ```

- Menghapus file dari server:

  ```
  DELETE PROTOKOL.txt
  ```

---
