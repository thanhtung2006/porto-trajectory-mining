> Notebook cùng thư mục: [porto_region_pilot.ipynb](porto_region_pilot.ipynb). [Về trang chủ repo](../../README.md).

> Các đường dẫn `data/`, `cache/`, `outputs/` trong tài liệu đều tính từ thư mục gốc repo. Notebook tự tìm thư mục gốc dù mở từ thư mục con. Các lệnh terminal trong README chạy từ gốc repo.

# Matching toàn bộ mẫu vùng C_8km

Mở **`porto_region_pilot.ipynb`**. Giữ tên notebook đã tạo từ pilot; cấu hình hiện tại xử lý đủ **9,501 chuyến trong mẫu EDA của vùng C_8km**.
Không đọc lại `train.csv`, không lấy thêm chuyến từ toàn dataset và không matching toàn bộ 1,7 triệu chuyến.

Hai notebook EDA và mô hình cũ được giữ nguyên trong lần thực thi này. Chưa train B0/B1/M1/M2 hoặc đánh giá ETA.

## Vùng nghiên cứu hiện tại

- Tên vùng: `C_8km`; kích thước danh nghĩa khoảng 8.0×8.0 km.
- Bbox `[west, south, east, north]`: `[-8.654504338104756, 41.12745663346633, -8.558716252527459, 41.199844416439696]`.
- Tâm/phạm vi: Center of C_4km; expanded in EPSG:32629 and enclosed by WGS84 bbox.
- Vùng đệm matching: 200 m. Nguồn graph: Verified original OSMnx Overpass raw-response cache.
- Với lần 8×8 km: raw cache Overpass được xác minh bằng SHA-1 truy vấn và polygon truy vấn thực; phủ đủ bbox + 200 m. Graph GraphML cũ chưa phủ vùng mới. Đệm 200 m thay cho 800 m là giới hạn ngữ cảnh ở biên cần ghi nhận.

## Cách chạy và cấu hình

1. Cài dependencies bằng `python -m pip install -r requirements/requirements_region_pilot.txt` nếu cần.
2. Giữ cache EDA đã tạo; nếu clone repo sang máy khác, cần dữ liệu và chạy EDA để tạo lại cache.
3. Mở notebook, chọn đúng kernel và Restart Kernel → Run All.
4. Cell A: `max_trips=9501`, bbox C_8km, đệm 200 m, tối đa 3 tiến trình CPU. Đặt 300 để trở lại pilot nhỏ.
5. Cùng cấu hình/code/graph và dữ liệu sẽ tái sử dụng các batch matching. Đổi cấu hình tạo cache khác.

Khi lấy hết pool 9,501 chuyến, giữ tất cả chuyến đủ điều kiện. Tỷ lệ giờ khởi hành là tỷ lệ có sẵn trong mẫu EDA, không ép 70/30 bằng cách bỏ chuyến.
joblib/loky chạy các batch độc lập, mỗi tiến trình có HMM/Rtree riêng và một luồng thư viện số. Các hàm nằm đầy đủ trong notebook.

## Kết quả thực thi trên dữ liệu thật

Lần mới nhất: `outputs/region_pilot/8946a3b89ff42fa9ba5c/`; con trỏ `outputs/region_pilot/latest_run.json`.
Mẫu thuộc 35 ngày giai đoạn train EDA đã khảo sát; các số liệu sau không phải tổng lưu lượng thành phố hoặc nhãn ùn tắc độc lập.

| Đại lượng | Kết quả |
|---|---:|
| Chuyến chọn / pool vùng C_8km | 9,501/9,501 |
| Taxi khác nhau | 426 |
| Ngày khởi hành | 35 |
| Đoạn context xử lý | 10,838 |
| Chuyến có context đủ điểm để matching | 9,489 |
| Graph bao gồm vùng đệm | 17,739 cạnh |
| Cạnh nằm hoàn toàn trong bbox | 15,464 |
| Cạnh có phần chiều dài dương trong bbox | 15,882 |
| Đoạn matcher trả kết quả | 10,583/10,838 |
| Đoạn đạt QA | 7,412/10,838 |
| Chuyến còn quan sát đạt QA trong bbox | 6,542/9,501 (68.9%) |
| Cạnh có quan sát đạt QA trong bbox | 7,539/15,882 (47.5%) |
| Độ phủ có trọng số chiều dài cạnh | 53.2% |
| Hợp chiều dài phần cạnh thực sự đi qua / chiều dài đường có hướng trong bbox | 51.2% |
| Traversals trong vùng | 213,448 |
| Cạnh × nhóm ngày × giờ có quan sát | 71,086/762,336 (9.3%) |
| Tổ hợp đủ ≥5 chuyến, ≥3 taxi, ≥3 ngày | 11,014 |

Có ít nhất một phần đạt QA không có nghĩa toàn bộ chuyến được giữ. Số cạnh đã quan sát không có nghĩa cạnh đó có đủ dữ liệu ở mọi giờ.

## Kiểm kê tất cả chuyến

| Trạng thái | Số chuyến |
|---|---:|
| Có ít nhất một khoảng quan sát đạt QA bên trong vùng | 6,542 |
| Không có đoạn đủ 4 điểm liên tục trong vùng đệm | 12 |
| Không có khoảng matcher hợp lệ (xem thêm cột lỗi) | 207 |
| Đạt QA ở context nhưng không còn quan sát đủ chất lượng trong vùng | 15 |
| Matcher trả kết quả nhưng các đoạn không đạt QA | 2,725 |

Đối chiếu từng TRIP_ID trong `outputs/csv/region_pilot/8946a3b89ff42fa9ba5c/trip_processing_status.csv`. Tổng các trạng thái bằng 9,501, không chỉ báo trên nhóm dễ matching.
Có 0/10,838 đoạn phát sinh exception khi chạy matcher hoặc phân bổ thời gian; đây là số lỗi thực thi, tách biệt với số đoạn không đạt QA. Chi tiết trong `segment_exception_counts.json` và cột n_segment_exceptions của bảng từng chuyến.
Khoảng đứng yên nhưng khớp nhiều cạnh không có cơ sở phân bổ thời gian theo khoảng cách. Bản hiện tại chỉ loại interval mơ hồ với mã ambiguous_stationary_edge_assignment, không nối qua khoảng bị loại và vẫn xét QA cho các interval còn lại. Đây là hiệu chỉnh so với lần B trước đó (loại cả đoạn context khi gặp lỗi phân bổ này); không so sánh hai vùng như thể cùng chính sách QA.
Khoảng đứng yên khớp rõ với một cạnh vẫn giữ duration và tốc độ 0. QA không phải nhãn đúng/sai độc lập cho lộ trình.

## Đọc kết quả

- `figures/01_region_road_graph.png`: bbox và mạng đường có đệm.
- `figures/02_matching_success_failure_examples.png`: ví dụ đạt/không đạt QA.
- `figures/03_matching_qa.png`: nguyên nhân loại khoảng GPS và độ lệch GPS–đường.
- `figures/04_observed_edges_and_time_coverage.png`: cạnh đã quan sát và độ phủ theo giờ Lisbon.
- `graph_counts.json`, `matching_metrics.json`, `coverage_metrics.json`: định nghĩa/mẫu số tách riêng.
- `region_matching_parts.parquet`, `edge_traversals.parquet`: offset, partial distance, thời gian, cờ nội suy và ID interval để dùng tiếp.
- **CSV tập trung**: `outputs/csv/region_pilot/8946a3b89ff42fa9ba5c/`.
- `matching_progress.json` và matching cache: batch hoàn tất được lưu ngay để tiếp tục sau gián đoạn.

## Giới hạn và kiểm tra

Lượt tiếp tục matching mất 15.4 phút với 3 tiến trình, đã tái sử dụng 164 batch / 4,100 đoạn từ lượt bị Windows khóa tệp tiến độ. Thời gian này không phải thời gian chạy mới toàn bộ dữ liệu. Chỉ hàm ghi JSON được bổ sung retry; AST các phần tính toán, cấu hình, phiên bản và dữ liệu đầu vào được đối chiếu giữ nguyên, Parquet tái sử dụng có SHA-256 giống từng byte. Chi tiết trong io_only_cache_recovery.json.
Graph lấy từ OSM hoặc cache phù hợp; nguồn, ngày tải/hash và cờ downloaded_now lưu trong graph_metadata.json. Mạng hiện tại có thể khác dữ liệu GPS năm 2013.
Vùng C_8km có 15,882 cạnh giao bbox và 17,739 cạnh khi tính cả vùng đệm. Không dùng số cạnh vùng đệm để thay số cạnh trong bbox; quy mô mới theo yêu cầu khoảng 8×8 km.
Timestamp giữ original_index và tính bằng UTC; khung giờ dùng Europe/Lisbon. Không nối qua khoảng trống hoặc các lần rời/vào bbox.
Thời gian giữa hai GPS được phân bổ theo tỷ lệ khoảng cách; các mảnh cạnh của cùng interval không phải các quan sát độc lập. Không dùng kết quả này để tự chứng minh tốc độ/nhãn ùn tắc chính xác.
Đã chạy toàn bộ notebook, fixture HMM/partial-edge, kiểm tra song song bằng tuần tự và cache, kiểm tra độc lập timestamp/ra-vào vùng/giờ-DST/bảo toàn thời gian. Báo cáo chi tiết ở notebook_verification.json và independent_verification.json.
Mẫu hiện tại thuộc giai đoạn train của EDA cũ. Chưa huấn luyện mô hình và chưa tính metric ETA trong lần này; cần chốt thiết kế train/validation/test trước bước đó.

??i chi?u cu?i: 13 fixture trong notebook v? 22 ki?m tra ??c l?p ??u ??t; t?ng ki?m k? 9.501 chuy?n kh?p b?ng l?a ch?n. Khi ??ng kernel, joblib/loky resource_tracker in hai KeyError khi d?n ???ng d?n th? m?c t?m; kh?ng ph?i l?i cell. B?n b??c ??u complete v? c?c b?ng ?? v??t qua ki?m tra ??c l?p. L?u th?ng b?o trong execution_notes.json; ch?a x? l? nguy?n nh?n c?a th?ng b?o d?n th? m?c t?m n?y.
