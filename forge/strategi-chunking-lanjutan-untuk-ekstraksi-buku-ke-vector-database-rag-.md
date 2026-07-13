# Strategi Chunking Lanjutan untuk Ekstraksi Buku ke Vector Database (RAG)

## Pendahuluan

**Strategi terbaik untuk melakukan *chunking* pada buku yang diekstrak ke Markdown adalah pendekatan *pipeline* multi-langkah: dimulai dengan pembersihan *noise* secara agresif, diikuti oleh segmentasi yang sadar struktur (berbasis *heading* dan paragraf), dan diakhiri dengan penyesuaian ukuran *chunk* dan *overlap* untuk menyeimbangkan antara presisi dan konteks.**

*Chunking* yang efektif adalah fondasi dari sistem RAG (Retrieval-Augmented Generation) yang akurat, terutama saat bekerja dengan dokumen panjang dan kompleks seperti buku. Proses ekstraksi dari format asli (misalnya PDF) ke Markdown sering kali menghasilkan banyak "noise"—artefak seperti *header/footer* halaman yang berulang, nomor halaman, kata yang terpotong akibat *line break*, dan kesalahan OCR [citation: 61] [citation: 75].

Strategi *chunking* yang sederhana, seperti memecah teks berdasarkan jumlah karakter atau token tetap (*fixed-size chunking*), sering kali gagal karena beberapa alasan utama:
*   **Amplifikasi Noise**: Metode ini tidak dapat membedakan antara konten inti dan noise. Akibatnya, *boilerplate* seperti *header* dan *footer* akan ikut di-*embed* dan mencemari *vector database*, menyebabkan *retrieval* yang tidak relevan [citation: 61].
*   **Kehilangan Batas Semantik**: Pemotongan teks secara arbitrer dapat memisahkan satu ide, kalimat, atau bahkan kata di tengah-tengah, merusak konteks yang dibutuhkan LLM untuk memberikan jawaban yang koheren [citation: 1] [citation: 7].
*   **Konteks Tidak Optimal**: *Chunk* yang terlalu kecil mungkin tidak memiliki konteks yang cukup, sementara *chunk* yang terlalu besar dapat mengencerkan informasi spesifik dan melampaui batas token model *embedding* [citation: 23] [citation: 32].

Oleh karena itu, diperlukan prinsip desain yang lebih canggih yang berfokus pada *noise suppression* dan penghormatan terhadap *semantic boundary*. Ini melibatkan *tradeoff* yang cermat antara ukuran *chunk*, tingkat *overlap* untuk menjaga kontinuitas, dan kebutuhan untuk menyediakan konteks yang cukup bagi LLM tanpa membanjirinya dengan informasi yang tidak relevan [citation: 32].


## Metode chunking berbasis aturan (rule-based) yang paling tahan noise

Pendekatan *chunking* berbasis aturan yang paling efektif untuk Markdown yang berasal dari buku (terutama yang melalui proses OCR) adalah dengan menerapkan *pipeline* multi-tahap yang memprioritaskan struktur semantik dokumen di atas metrik arbitrer seperti jumlah karakter. Strategi ini secara fundamental memperlakukan *chunking* sebagai "masalah semantik, bukan masalah teks" [citation: 44]. *Pipeline* ini dirancang untuk memisahkan dokumen berdasarkan *heading* terlebih dahulu, baru kemudian memecahnya lebih lanjut berdasarkan batas linguistik alami seperti paragraf dan kalimat, sambil mempertahankan integritas elemen-elemen penting seperti tabel dan blok kode.

### Pipeline Segmentasi: *Parse → Sectionise → Sentence/Paragraphise*

Alih-alih langsung memotong teks, *pipeline* yang lebih tangguh mengikuti urutan logis untuk memastikan setiap *chunk* yang dihasilkan memiliki konteks yang maksimal dan *noise* yang minimal.

1.  ***Parse (Pre-processing & Noise Removal)***: Tahap ini adalah fondasi terpenting. Sebelum segmentasi dilakukan, teks mentah harus dibersihkan dari artefak ekstraksi. Tujuannya adalah untuk menghilangkan "junk text" yang jika ter-indeks akan menciptakan klaster *embedding* yang tidak relevan dan menurunkan kualitas *retrieval* [citation: 61].
    *   **Hapus *Boilerplate***: Identifikasi dan hapus *header*, *footer*, dan nomor halaman yang berulang. Heuristik yang efektif adalah dengan mengidentifikasi baris teks yang muncul secara frekuen di bagian atas atau bawah di sebagian besar halaman [citation: 73] [citation: 74], atau dengan mengabaikan teks yang berada di margin posisi tertentu [citation: 75].
    *   **Perbaiki Artefak OCR**: Lakukan normalisasi spasi berlebih, perbaiki kata-kata yang terpotong oleh *line break* (*de-hyphenation*), dan bersihkan simbol-simbol acak yang tidak relevan [citation: 61] [citation: 72]. Penggunaan LLM untuk mengoreksi kesalahan OCR juga merupakan pendekatan modern yang efektif [citation: 77].

2.  ***Sectionise (Segmentasi Berbasis Heading)***: Setelah teks bersih, langkah selanjutnya adalah membaginya menjadi bagian-bagian logis berdasarkan struktur hierarkis dokumen.
    *   **Gunakan *Header* sebagai Batas Utama**: Manfaatkan *splitter* yang sadar-struktur seperti `MarkdownHeaderTextSplitter` dari LangChain. Komponen ini secara spesifik dirancang untuk memecah dokumen berdasarkan level *heading* (`#`, `##`, `###`) dan menyimpan hierarki tersebut sebagai metadata [citation: 51] [citation: 54]. Ini sejalan dengan prinsip *Document Structure-Based Chunking* yang terbukti efektif untuk dokumen terstruktur [citation: 41].

3.  ***Sentence/Paragraphise (Segmentasi Berbasis Batas Linguistik)***: Setiap "section" yang dihasilkan dari tahap sebelumnya mungkin masih terlalu besar. Tahap ini memecah section tersebut lebih lanjut dengan menghormati batas-batas linguistik alami.
    *   **Prioritaskan Paragraf**: Gunakan pemisah paragraf (misalnya, baris kosong atau `\n\n`) sebagai batas pemotongan pertama di dalam sebuah *section* [citation: 62].
    *   **Gunakan Kalimat sebagai Cadangan**: Jika sebuah paragraf masih melebihi batas ukuran *chunk* yang diinginkan, baru pecah berdasarkan batas kalimat (misalnya, setelah tanda titik, tanya, atau seru) [citation: 1].
    *   **Jaga Konsistensi *Overlap***: Saat menerapkan *overlap* untuk menjaga kontinuitas, pastikan *overlap* tersebut tidak melintasi batas *section* yang telah ditentukan pada tahap *Sectionise*. Hal ini untuk mencegah konteks dari dua *heading* yang berbeda tercampur dalam satu *chunk* [citation: 51].

### Aturan Pengecualian: Elemen yang Tidak Boleh Dipisah (*Do-Not-Split Rules*)

Untuk menjaga integritas semantik, beberapa elemen dalam Markdown harus diperlakukan sebagai unit atomik yang tidak boleh dipecah di tengah-tengah. Menerapkan aturan "do-not-split" sangat penting untuk mencegah hilangnya informasi terstruktur.

*   **Blok Kode**: Memotong blok kode di tengah dapat membuatnya tidak valid secara sintaksis dan menghilangkan konteks penting bagi pengembang. LlamaIndex dan LangChain menyediakan *splitter* khusus kode yang dapat memecah berdasarkan unit bahasa (misalnya, fungsi atau kelas) [citation: 42] [citation: 43].
*   **Tabel**: Tabel Markdown kehilangan semua maknanya jika baris atau kolomnya dipisahkan ke dalam *chunk* yang berbeda. Seluruh tabel harus disimpan dalam satu *chunk* tunggal [citation: 44] [citation: 62].
*   **Daftar (*Lists*) dan *Admonitions***: Daftar bernomor atau berpoin, serta blok khusus seperti catatan atau peringatan (*callouts*), membawa makna kolektif. Memisahkan item-item ini dapat merusak alur logika atau instruksi [citation: 62].
*   **Judul dan Paragraf Pertama**: Hindari memisahkan *heading* dari paragraf pertama yang mengikutinya. Paragraf pembuka ini biasanya berisi ringkasan atau pengenalan krusial untuk sisa konten di bawah *heading* tersebut [citation: 62].

### Desain Metadata: Manfaat `section_path` untuk Konteks

Saat melakukan segmentasi berbasis *heading*, metadata menjadi sama pentingnya dengan konten *chunk* itu sendiri. Menyimpan "jejak" atau jalur hierarkis dari mana sebuah *chunk* berasal memberikan konteks yang sangat berharga selama proses *retrieval*.

*   **Implementasi `section_path`**: `MarkdownHeaderTextSplitter` secara otomatis menambahkan metadata yang berisi *heading* yang relevan untuk setiap *chunk* [citation: 51] [citation: 57]. Ini dapat diformat menjadi sebuah *breadcrumb* atau `section_path`, misalnya: `{"source": "buku_ai.md", "section_path": ["Bab 3: Model Transformer", "Sub-bab 3.2: Arsitektur Attention"]}`.
*   **Manfaat untuk Disambiguasi**: `section_path` membantu membedakan antara *chunk* dengan konten yang mungkin mirip tetapi berasal dari bagian buku yang berbeda. Ini mengurangi ambiguitas dan meningkatkan presisi *retrieval* [citation: 62].
*   **Mendukung Strategi *Retrieval* Lanjutan**: Metadata ini sangat penting untuk strategi seperti *parent-child chunking* atau *auto-merging retrieval*, di mana sistem dapat mengambil *chunk* induk yang lebih besar (misalnya, seluruh sub-bab) ketika beberapa *chunk* anak dari jalur yang sama terbukti relevan [citation: 42].

---

## Chunking hierarkis & retrieval-friendly (parent-child / auto-merging)

**Strategi *chunking* hierarkis, yang sering diimplementasikan melalui pola *parent-child*, secara efektif menjembatani dilema antara presisi dan konteks dalam sistem RAG.** Pendekatan ini sangat berguna untuk dokumen panjang seperti buku, di mana sebuah jawaban mungkin memerlukan kutipan spesifik (*specific evidence*) yang tertanam dalam konteks naratif yang lebih luas (*broad context*). Idenya adalah memisahkan unit yang diindeks untuk pencarian (*retrieval*) dari unit yang disajikan ke LLM untuk sintesis jawaban [citation: 24].

Daripada mengindeks *chunk* berukuran sedang yang merupakan kompromi, strategi ini menciptakan dua atau lebih level representasi dokumen. *Chunk* anak (*child chunks*) yang lebih kecil dan padat secara semantik di-*embed* dan diindeks untuk pencarian vektor yang sangat presisi, sementara *chunk* induk (*parent chunks*) yang lebih besar disimpan untuk menyediakan konteks penuh saat dibutuhkan [citation: 24] [citation: 26].

### Kapan Hierarchical Chunking Paling Berguna untuk Buku?

Pendekatan ini tidak selalu diperlukan, tetapi menjadi sangat kuat dalam skenario spesifik yang umum ditemui saat memproses buku:

*   **Jawaban Membutuhkan Konteks Lintas Paragraf**: Ketika sebuah pertanyaan tidak dapat dijawab oleh satu paragraf saja, melainkan membutuhkan pemahaman dari seluruh sub-bab atau bagian. Misalnya, pertanyaan "Jelaskan dampak arsitektur Transformer terhadap perkembangan NLP" membutuhkan lebih dari sekadar definisi *attention mechanism*.
*   **Dokumen dengan Kepadatan Informasi Tinggi**: Untuk buku teknis, makalah akademis, atau dokumen legal, di mana setiap kalimat bisa jadi krusial. *Child chunk* yang kecil (misalnya, 2-3 kalimat) dapat mencapai presisi tinggi dalam menemukan fakta spesifik [citation: 24].
*   **Mengurangi Masalah "Lost in the Middle"**: LLM cenderung lebih memperhatikan informasi di awal dan akhir konteks yang diberikan. Dengan mengambil *parent chunk* yang lebih besar dan relevan, informasi penting yang mungkin tersebar di beberapa *child chunk* dapat disatukan, memastikan LLM menerima narasi yang koheren dan mengurangi risiko informasi kunci "tenggelam" di tengah *prompt* [citation: 7] [citation: 24].

### Mekanisme Parent-Child dan Auto-Merging

Implementasi praktis dari *chunking* hierarkis sering kali menggunakan konsep *Auto-Merging Retriever*, seperti yang tersedia di LlamaIndex dan Haystack. Proses ini bekerja dalam dua langkah utama saat *query* dieksekusi.

1.  ***Retrieval* pada Level Anak (*Child Level*)**: Awalnya, pencarian kesamaan vektor dilakukan terhadap *child chunk* yang kecil dan terindeks. Langkah ini bertujuan untuk menemukan potongan-potongan informasi yang paling relevan secara semantik dengan presisi tinggi.

2.  ***Merging* ke Level Induk (*Parent Level*)**: Setelah beberapa *child chunk* yang relevan ditemukan, sistem akan memeriksa metadata mereka (misalnya, `parent_id`). Jika sejumlah *chunk* yang diambil (berdasarkan ambang batas atau *threshold* yang ditentukan) berasal dari *parent chunk* yang sama, *retriever* akan secara otomatis "menggabungkan" atau menggantinya dengan *parent chunk* tersebut [citation: 26] [citation: 42].

Misalnya, jika *retriever* menemukan tiga *child chunk* yang relevan dan ketiganya berasal dari "Bab 5, Sub-bab 2", sistem tidak akan mengirimkan tiga potongan kecil itu ke LLM, melainkan mengambil seluruh teks dari "Sub-bab 2" sebagai satu konteks yang utuh.

#### Implementasi dalam Framework

*   **LlamaIndex**: Menggunakan `HierarchicalNodeParser` untuk membuat struktur node dengan referensi *parent-child*. Ini kemudian digunakan bersama dengan `AutoMergingRetriever` yang secara otomatis mengganti node anak dengan node induknya selama proses *retrieval* [citation: 2] [citation: 42].
*   **Haystack**: Menyediakan `HierarchicalDocumentSplitter` untuk membuat struktur dokumen multi-level dan `AutoMergingRetriever` yang mengembalikan dokumen induk jika ambang batas *child chunk* yang cocok dari induk yang sama terpenuhi [citation: 21] [citation: 26]. Komponen ini memungkinkan konfigurasi `block_sizes` (misalnya, `{20, 5}` untuk induk 20 unit dan anak 5 unit) dan `split_by` ('kalimat', 'kata', dll.) [citation: 21].

### Menghubungkan dengan Ukuran Chunk Menengah

Strategi *parent-child* secara efektif menciptakan "ukuran *chunk* dinamis" yang beradaptasi dengan kebutuhan *query*. Meskipun kita mengindeks *chunk* yang sangat kecil (misalnya, 256 token) untuk presisi, konteks yang akhirnya diberikan ke LLM bisa setara dengan *chunk* berukuran sedang atau besar (misalnya, 1024-2048 token) jika strategi *auto-merging* terpicu [citation: 24].

| Aspek | Child Chunk (Untuk Retrieval) | Parent Chunk (Untuk Konteks LLM) |
| :--- | :--- | :--- |
| **Tujuan** | Presisi pencarian tinggi, menemukan "jarum" | Konteks luas, memberikan gambaran besar |
| **Ukuran Tipikal** | Kecil (mis., 200-400 token) [citation: 24] | Sedang hingga Besar (mis., 2000+ token) [citation: 24] |
| **Proses** | Di-*embed* dan diindeks di *vector store* | Disimpan di *document store* dan diambil melalui *metadata ID* |
| **Kelebihan** | Mengurangi *noise* dalam pencarian, target spesifik | Memberikan narasi utuh, mengurangi "lost in the middle" |

Pendekatan ini menawarkan yang terbaik dari kedua dunia: **presisi pencarian dari *chunk* kecil dan kekayaan kontekstual dari *chunk* besar**, tanpa harus memilih satu ukuran tetap yang kaku di awal. Ini adalah strategi lanjutan yang sangat direkomendasikan untuk RAG berbasis buku di mana kedalaman dan keluasan konteks sama-sama penting.


## Pipeline preprocessing untuk menghilangkan OCR/scan noise sebelum chunking

**Kualitas *retrieval* dalam sistem RAG berbanding lurus dengan kualitas teks yang diindeks.** Sebelum melakukan segmentasi struktural yang canggih, langkah paling fundamental dan berdampak tinggi adalah membersihkan *noise* yang berasal dari proses ekstraksi, terutama dari dokumen yang dipindai (OCR). Mengabaikan tahap ini akan menyebabkan *embedding* dipenuhi oleh "teks sampah" (*junk text*), yang secara konsisten akan ditarik oleh *retriever* dan merusak akurasi jawaban [citation: 61].

Sebuah *pipeline* *preprocessing* yang efektif berfokus pada serangkaian tugas pembersihan yang dilakukan **sebelum** teks dipecah berdasarkan *heading* atau struktur semantik lainnya. Tujuannya adalah untuk menormalkan teks ke dalam format yang bersih dan konsisten, memastikan bahwa hanya konten substantif yang di-*embed*.

### Fase 1: Normalisasi Teks dan Perbaikan Struktural

Langkah pertama adalah memperbaiki artefak level karakter dan baris yang umum dihasilkan oleh OCR.

#### Normalisasi *Whitespace* dan *Line Breaks*
Teks hasil OCR sering kali mengandung spasi yang tidak beraturan dan pemutusan baris yang salah yang merusak alur kalimat.
*   **Gabungkan spasi berlebih**: Gunakan Regex untuk mengubah beberapa spasi atau tab menjadi satu spasi tunggal.
*   **Perbaiki pemutusan baris (line wrap)**: Heuristik yang umum digunakan adalah menggabungkan baris yang tidak diakhiri dengan tanda baca terminal (titik, tanda tanya, seru) dengan baris berikutnya. Ini sangat penting untuk menyatukan kembali kalimat yang terpotong karena batas kolom atau margin halaman [citation: 77].

#### De-hyphenation
Kata-kata yang terpotong di akhir baris adalah masalah klasik dalam ekstraksi PDF dan OCR.
*   **Perbaikan kata dengan tanda hubung**: Identifikasi dan gabungkan kembali kata-kata yang dipisahkan oleh tanda hubung dan *newline* (misalnya, `comput-\nation` menjadi `computation`). Beberapa *library* ekstraksi teks seperti MuPDF telah meningkatkan penanganan *soft* dan *hard hyphens* untuk memitigasi masalah ini secara otomatis [citation: 71] [citation: 72].

### Fase 2: Penghapusan *Boilerplate* Berulang

*Boilerplate* seperti *header*, *footer*, dan nomor halaman adalah sumber *noise* terbesar karena sifatnya yang berulang di banyak halaman. Menghapusnya sangat penting untuk mencegah *vector database* didominasi oleh konten yang tidak relevan ini [citation: 61] [citation: 82].

#### Pendekatan Berbasis Frekuensi (*Frequency-Based*)
Metode ini mengasumsikan bahwa teks *header* dan *footer* adalah baris yang sama (atau sangat mirip) yang muncul berulang kali di seluruh dokumen.
*   **Mekanisme**: Ekstrak teks halaman per halaman. Hitung frekuensi kemunculan setiap baris teks di bagian atas (misalnya, 3 baris pertama) dan bawah (misalnya, 3 baris terakhir) dari setiap halaman. Baris yang muncul di sebagian besar halaman (misalnya, >80%) dianggap sebagai *header* atau *footer* dan dihapus [citation: 73] [citation: 74].
*   **Kelebihan**: Sangat efektif untuk dokumen dengan *header/footer* yang konsisten dan tidak bergantung pada tata letak geometris yang presisi.

#### Pendekatan Berbasis Posisi (*Position-Based*)
Metode ini bekerja dengan mendefinisikan zona "margin" di bagian atas dan bawah halaman dan mengabaikan semua teks yang jatuh di dalam zona tersebut.
*   **Mekanisme**: Saat mengekstrak teks dengan *tool* yang menyediakan koordinat (x, y), definisikan area *bounding box* untuk *header* dan *footer* (misalnya, 10% teratas dan 10% terbawah dari tinggi halaman). Semua teks yang berada dalam zona ini akan dibuang [citation: 75].
*   **Kelebihan**: Berguna untuk dokumen di mana konten *header/footer* mungkin sedikit bervariasi (misalnya, menyertakan judul bab yang berubah), tetapi posisinya tetap statis.

| Metode Penghapusan | Cara Kerja | Kapan Digunakan |
| :--- | :--- | :--- |
| **Berbasis Frekuensi** | Mengidentifikasi baris teks yang berulang di banyak halaman [citation: 73]. | Dokumen dengan *header/footer* teks yang identik di setiap halaman. |
| **Berbasis Posisi** | Mengabaikan teks dalam zona geometris yang telah ditentukan (margin atas/bawah) [citation: 75]. | Dokumen dengan tata letak yang konsisten, bahkan jika teks *header/footer* sedikit berubah. |

### Fase 3: Dedupikasi Konten

Setelah *noise* spesifik halaman dihilangkan, mungkin masih ada konten duplikat yang lebih besar, seperti paragraf disclaimer hukum atau kutipan yang diulang di beberapa bab.
*   **Dedupikasi Tepat dan Hampir-Duplikat**: Terapkan algoritma untuk mengidentifikasi dan menghapus *chunk* teks yang identik atau sangat mirip. Ini lebih lanjut mengurangi redundansi dalam *vector store* dan memastikan setiap *embedding* mewakili potongan informasi yang unik [citation: 61] [citation: 62].

Penyelesaian *pipeline* *preprocessing* ini **sebelum** menerapkan *splitter* berbasis *heading* atau semantik memastikan bahwa proses *chunking* selanjutnya bekerja pada representasi konten buku yang paling bersih dan paling akurat, yang merupakan prasyarat untuk membangun sistem RAG yang andal dan berkinerja tinggi.
## Saran parameter awal & template eksperimen (A/B)

Setelah menerapkan *pipeline* pembersihan dan segmentasi struktural, langkah selanjutnya adalah menyetel parameter kunci—`chunk_size` dan `chunk_overlap`—dan secara sistematis mengevaluasi dampaknya terhadap kualitas *retrieval*. Tidak ada satu set parameter yang "sempurna" untuk semua kasus; nilai optimal sangat bergantung pada karakteristik konten buku dan jenis pertanyaan yang diharapkan. Oleh karena itu, pendekatan terbaik adalah memulai dengan *baseline* yang terinformasi oleh riset dan melakukan eksperimen A/B untuk menemukan konfigurasi yang paling efektif.

### Parameter Awal yang Direkomendasikan

Berdasarkan berbagai *benchmark* dan praktik industri, berikut adalah titik awal yang kuat untuk eksperimen Anda.

#### Ukuran Chunk (`chunk_size`)
Ukuran *chunk* adalah *trade-off* antara presisi dan kelengkapan konteks. *Chunk* yang lebih kecil lebih presisi dalam pencarian, sementara *chunk* yang lebih besar memberikan lebih banyak konteks kepada LLM.

*   **Baseline Umum (Prosa & Narasi)**: Mulailah dengan rentang **256–512 token**. *Benchmark* dari NVIDIA menunjukkan bahwa ukuran *chunk* di rentang ini memberikan kinerja yang stabil dan kuat di berbagai jenis dataset [citation: 31].
*   **Konten Analitis atau Kompleks**: Untuk pertanyaan yang membutuhkan penalaran atau penjelasan mendalam (misalnya, membandingkan konsep, menjelaskan proses), ukuran *chunk* yang lebih besar sering kali lebih baik. Pertimbangkan rentang **512–1024 token** untuk memastikan argumen atau penjelasan yang koheren tidak terpotong [citation: 31] [citation: 24].
*   **Dokumen dengan Struktur Halaman yang Kuat**: Jika buku Anda memiliki struktur per halaman yang jelas (misalnya, buku manual atau laporan terstruktur), ***page-level chunking*** sering kali menjadi *default* yang paling andal, mengungguli strategi berbasis token dalam beberapa *benchmark* [citation: 31].
*   **Hindari Ukuran Ekstrem**: Kinerja cenderung menurun pada ukuran *chunk* yang sangat kecil (misalnya, 128 token) karena kurangnya konteks, atau sangat besar (misalnya, 2048 token) karena informasi menjadi terlalu encer dan berisiko melampaui batas konteks model *embedding* [citation: 31] [citation: 23].

#### Overlap Antar Chunk (`chunk_overlap`)
*Overlap* berfungsi sebagai jaring pengaman untuk mencegah informasi penting terpotong di batas antar *chunk*.

*   **Aturan Umum**: *Baseline* yang paling umum direkomendasikan adalah **10–20% dari `chunk_size`**. Ini dianggap sebagai keseimbangan yang baik antara menjaga kontinuitas konteks dan meminimalkan redundansi data serta biaya *embedding* [citation: 1] [citation: 16] [citation: 23].
*   **Contoh Praktis**: Untuk `chunk_size` sebesar 512 token, *overlap* sebesar **50–100 token** adalah titik awal yang masuk akal [citation: 16].
*   **Penyesuaian**: Jika Anda menemukan bahwa *retrieval* sering kali "nyaris benar" tetapi kehilangan kalimat kunci di awal atau akhir, tingkatkan *overlap*. Sebaliknya, jika hasil pencarian terlalu redundan, pertimbangkan untuk menurunkannya [citation: 32].

### Skema Eksperimen A/B untuk Evaluasi

Untuk mengukur secara objektif apakah perubahan strategi *chunking* benar-benar meningkatkan kinerja, rancanglah sebuah kerangka evaluasi yang terstruktur.

#### Langkah 1: Siapkan "Golden Set" Evaluasi
Buat satu set data evaluasi yang terdiri dari:
1.  **Pertanyaan Representatif**: Kumpulan pertanyaan yang mencerminkan kasus penggunaan nyata (misalnya, 10-20 pertanyaan). Sertakan campuran pertanyaan faktual (siapa, apa, kapan) dan analitis (mengapa, bagaimana, jelaskan) [citation: 31].
2.  **Konteks Ideal yang Dilabeli**: Untuk setiap pertanyaan, identifikasi secara manual dan catat satu atau lebih bagian (pasal/paragraf) dari buku yang berisi jawaban yang benar dan lengkap. Ini akan menjadi "ground truth" Anda [citation: 62].

#### Langkah 2: Definisikan Konfigurasi untuk Diuji
Pilih dua atau lebih konfigurasi untuk dibandingkan. Misalnya:

*   **Konfigurasi A (Baseline)**:
    *   Strategi: *Recursive Character Splitting*
    *   `chunk_size`: 512 token
    *   `chunk_overlap`: 50 token
*   **Konfigurasi B (Hipotesis Perbaikan)**:
    *   Strategi: *Parent-Child* dengan *Auto-Merging*
    *   `chunk_size` (anak): 256 token
    *   `chunk_overlap` (anak): 25 token
    *   `parent_chunk_size`: 1024 token

#### Langkah 3: Jalankan Eksperimen dan Ukur Metrik Kunci
Untuk setiap konfigurasi, jalankan semua pertanyaan dari "golden set" Anda melalui *retriever* dan ukur metrik berikut.

| Metrik Evaluasi | Deskripsi | Cara Mengukur |
| :--- | :--- | :--- |
| **Context Precision** | Seberapa relevan *chunk* yang diambil? Apakah semua *chunk* yang dikembalikan benar-benar berhubungan dengan pertanyaan? | Dari *chunk* yang diambil, hitung persentase yang cocok dengan "konteks ideal" yang telah Anda labeli. |
| **Context Recall** | Apakah *retriever* berhasil menemukan semua informasi yang relevan? | Dari semua "konteks ideal" yang seharusnya ditemukan, hitung persentase yang berhasil diambil oleh *retriever*. Metrik Recall@K adalah standar di sini [citation: 62]. |
| **Faithfulness** | Apakah jawaban yang dihasilkan oleh LLM sepenuhnya didukung oleh konteks yang diambil? | Periksa jawaban LLM dan pastikan tidak ada informasi yang bertentangan atau "berhalusinasi" di luar konteks yang diberikan. |
| **Answer Relevancy** | Seberapa baik jawaban LLM benar-benar menjawab pertanyaan pengguna? | Nilai secara subjektif (atau gunakan LLM sebagai juri) apakah jawaban tersebut memuaskan dan relevan dengan maksud pertanyaan. |

Alat seperti **RAGAs** dapat membantu mengotomatiskan pengukuran metrik-metrik ini, memberikan skor kuantitatif untuk *Faithfulness* dan *Answer Relevancy* [citation: 32]. Dengan membandingkan skor metrik ini antara Konfigurasi A dan B, Anda dapat membuat keputusan berbasis data tentang strategi *chunking* mana yang memberikan hasil terbaik untuk kasus penggunaan spesifik Anda.## Arsitektur implementasi: local CPU/GPU vs API (kombinasi bebas)

Strategi *chunking* yang paling efektif untuk buku yang diekstrak ke Markdown yang penuh *noise* adalah *pipeline* multi-langkah yang memprioritaskan pembersihan agresif, diikuti oleh segmentasi berbasis struktur, dan dapat ditingkatkan dengan *retrieval* hierarkis. Meskipun *chunking* dapat sepenuhnya berbasis aturan dan dijalankan secara lokal (CPU/GPU), penggunaan API untuk LLM dapat membantu pada tahap-tahap tertentu seperti pembersihan *noise* tingkat lanjut atau *reranking*.

**Key Findings:**
*   **Pembersihan Noise adalah Fondasi**: Kualitas *retrieval* lebih ditentukan oleh pembersihan teks awal daripada algoritma *chunking* itu sendiri. Menghapus *boilerplate* OCR seperti *header*, *footer*, dan *hyphenation* yang salah secara sistematis sebelum segmentasi adalah langkah paling krusial [citation: 61] [citation: 73] [citation: 75].
*   **Segmentasi Berbasis Struktur Lebih Unggul**: Pendekatan berbasis aturan yang paling andal adalah *structure-aware chunking*, yang menggunakan *heading* sebagai batas semantik utama, kemudian memecah lebih lanjut berdasarkan paragraf. Metode ini secara konsisten lebih unggul daripada pemotongan berdasarkan ukuran tetap karena menjaga konteks dokumen [citation: 51] [citation: 62].
*   **Hierarki untuk Keseimbangan Konteks dan Presisi**: Strategi *parent-child* dengan *auto-merging* menawarkan solusi canggih untuk menyeimbangkan kebutuhan akan presisi pencarian (menggunakan *child chunk* kecil) dan kekayaan konteks untuk LLM (mengambil *parent chunk* besar). Ini sangat efektif untuk dokumen yang padat dan kompleks seperti buku [citation: 24] [citation: 26] [citation: 42].
*   **Parameter Awal dan Evaluasi Sistematis**: Tidak ada ukuran *chunk* universal. Titik awal yang baik adalah 256-512 token dengan *overlap* 10-20%, namun konfigurasi terbaik harus divalidasi melalui eksperimen A/B menggunakan metrik seperti *Context Recall* dan *Precision* pada set data evaluasi yang representatif [citation: 31] [citation: 16] [citation: 62].

Analisis ini telah membahas berbagai metode, rekomendasi, dan strategi gabungan untuk melakukan *chunking* pada file Markdown yang bising untuk digunakan sebagai *database vector*, yang dapat diimplementasikan menggunakan sumber daya lokal maupun API.