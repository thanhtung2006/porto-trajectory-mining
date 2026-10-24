> Notebook cùng thư mục: [porto_region_coverage_expansion.ipynb](porto_region_coverage_expansion.ipynb). [Về trang chủ repo](../../README.md).

> Các đường dẫn `data/`, `cache/`, `outputs/` trong tài liệu đều tính từ thư mục gốc repo. Notebook tự tìm thư mục gốc dù mở từ thư mục con. Các lệnh terminal trong README chạy từ gốc repo.

# Bổ sung chuyến để tăng độ phủ vùng C 8×8 km

Mở `porto_region_coverage_expansion.ipynb`. Notebook giữ nguyên vùng và graph của lần
matching trước, dùng lại quan sát từ 9.501 chuyến và chỉ matching chuyến mới từ `train.csv`.
Baseline có 7.539/15.882 cạnh với ít nhất một quan sát đạt QA. Mục tiêu là tăng độ phủ
bằng dữ liệu thật; chưa bảo đảm mọi cạnh đều có taxi được dataset ghi nhận.
Giai đoạn train mặc định: từ 01/07 đến trước 05/08/2013, giờ `Europe/Lisbon`.

## Chạy notebook

1. Cài package nếu cần: `python -m pip install -r requirements/requirements_region_pilot.txt`.
2. Giữ dữ liệu, cache EDA và thư mục baseline matching đã tạo. Các thư mục này được
   gitignore, nên khi clone sang máy mới phải tạo/chuyển chúng riêng.
3. Trong cell **A. Cấu hình**, sửa `data_path` nếu cần. Hỗ trợ CSV hoặc ZIP chứa `train.csv`;
   `zip_member` xác định tên thành viên nếu ZIP không có đúng một `train.csv`.
4. Restart Kernel → Run All. Cấu hình hiện tại `max_additional_trips_per_round=5000`, `max_rounds=5`:
   đợt 1–3 dùng lại 15.000 chuyến bổ sung đã hoàn tất; đợt 4–5 thêm 10.000 chuyến mới.
   Có thể đặt 100 chuyến để kiểm tra matching nhỏ; kết quả đó không đủ cho kết luận giao thông.
   `matching_workers=6` đã được chọn cho máy hiện tại 16 nhân vật lý, RAM 32 GB;
   giảm còn 2–3 nếu chạy trên máy ít RAM/CPU hơn. Thay số tiến trình vẫn dùng lại batch đã lưu.
5. Muốn thêm một đợt sau năm đợt này, tăng `max_rounds` lên 6 rồi Run All. Giữ nguyên ngân sách mỗi đợt,
   seed, vùng và ngưỡng để tái sử dụng đúng các đợt cũ.

## Các bước xử lý

- Kiểm tra cấu hình và SHA-256 baseline; giữ graph, ID cạnh và ngưỡng QA.
- Kiểm tra SHA-256 nội dung CSV với metadata SQLite của EDA. Quét theo chunk, chỉ
  parse các chuyến hợp lệ trong train, loại TRIP_ID của toàn bộ mẫu 10.000 ban đầu.
- Loại chuyến vượt qua ranh giới kết thúc train. Giữ timestamp gốc và original_index,
  tách nhảy GPS/khoảng trống, giữ điểm đứng yên như cleaning EDA.
- Cache ứng viên và GPS context theo shard. Ô lưới 200 m giúp xếp hạng ứng viên gần
  các cạnh còn thiếu, không được dùng làm bằng chứng cạnh đã có taxi đi qua.
- Chọn mẫu có seed, ưu tiên độ phủ còn thiếu và giới hạn tỷ trọng ngày/taxi.
  Đây là mẫu chủ đích; không dùng để suy ra tỷ lệ nhu cầu toàn vùng.
- Chạy Leuven HMM trên chuyến mới, QA và cắt partial-edge về bbox. Gộp với baseline
  bằng TRIP_ID không trùng; đo mức tăng coverage thực sau mỗi đợt.
- Dừng khi hết số đợt cấu hình, đạt mục tiêu, hết ứng viên hoặc tăng quá ít cạnh.
  Cạnh chưa được quan sát vẫn giữ nguyên trong graph và mang trạng thái thiếu dữ liệu.

## Kết quả và cache

Con trỏ lượt hoàn tất mới nhất: `outputs/region_coverage_expansion/latest_run.json`.

- CSV: `outputs/csv/region_coverage_expansion/<run_key>/`.
- JSON, Parquet, PNG: `outputs/region_coverage_expansion/<run_key>/`.
- `round_metrics`: số chuyến mới, số cạnh tăng thêm và coverage lũy kế.
- `edge_observation_status`: tất cả cạnh trong vùng, trạng thái và nguồn quan sát.
- `remaining_unobserved_edges`: các cạnh chưa có quan sát QA trong tập đã chọn.
- `combined_region_matching_parts`, `combined_edge_traversals`, `combined_edge_time_coverage`:
  dữ liệu gộp để tiếp tục xây thống kê lịch sử sau này.
- `figures/01_incremental_edge_coverage.png`: baseline xanh, cạnh mới cam, chưa quan sát xám.
- `verification.json` và `notebook_verification.json`: kiểm chứng kết quả thực thi.

Cache ứng viên tách khỏi số đợt; tăng `max_rounds` không quét lại CSV và không matching
lại chuyến cũ. Các batch matching hoàn tất được lưu ngay để tiếp tục sau gián đoạn.
SHA-256 nội dung được xác minh ở lần đầu; những lần sau kiểm tra fingerprint đường dẫn,
kích thước và mtime để dùng lại hash. Đặt `verify_full_hash=True` nếu cần băm lại toàn bộ tệp.

## Giới hạn

Coverage 100% chỉ nói mỗi cạnh có ít nhất một quan sát QA, chưa nói đủ taxi, ngày và giờ.
Phải kiểm tra hỗ trợ theo cạnh × nhóm ngày × giờ trước khi train mô hình.
Các bảng quan sát gộp được xử lý trong RAM; tăng số đợt dần và theo dõi RSS tại `runtime.json`.
Validation/test sẽ lấy độc lập theo thời gian; chưa chạy model hoặc đánh giá ETA trong notebook này.
Graph OSM hiện tại có thể khác năm 2013; matching có sai số và QA không phải nhãn xác nhận độc lập.
Phân bổ thời gian qua các cạnh trong 15 giây dựa trên tỷ lệ quãng đường, có cờ nội suy.
Ứng viên phải có ít nhất một GPS sau cleaning nằm trong bbox, kể cả chuyến bắt đầu ngoài vùng.
Chuyến chỉ cắt qua góc vùng giữa hai GPS nhưng không có điểm trong bbox chưa thuộc pool này;
GPS 15 giây và tiêu chí chọn ứng viên cũng là giới hạn khi hướng tới độ phủ toàn bộ cạnh.

## Kết quả thực thi trên dữ liệu thật

Lượt hoàn tất: `outputs/region_coverage_expansion/a3bc4981c0524eb0f19f`.

| Đại lượng | Kết quả |
|---|---:|
| Chuyến bổ sung đã chọn | 25,000 |
| Chuyến baseline + bổ sung | 34,501 |
| Cạnh baseline | 7,539 |
| Cạnh QA mới nhờ bổ sung | 3,574 |
| Cạnh có quan sát QA lũy kế | 11,113/15,882 (70.0%) |
| Cạnh còn thiếu quan sát trong tập đã chọn | 4,769 |
| Tổ hợp cạnh × nhóm ngày × giờ đủ hỗ trợ | 52,868 |

Lý do dừng: `configured_round_budget_reached`. Chưa tuyên bố đã phủ toàn bộ cạnh.
Các chuyến bổ sung trải qua 35 ngày và 428 TAXI_ID.
Kiểm tra độc lập: 44 kiểm tra đạt; 0 exception ở cấp đoạn matching.
Chi tiết từng đợt, thời gian chạy và cache hit ở `round_metrics.parquet`, `runtime.json` và `round_*/matching_cache.json`.

Lần bổ sung mới nhất giữ nguyên 24,501 chuyến đã chọn và thêm đúng 10,000 TRIP_ID mới. Số cạnh có quan sát QA tăng từ 10,840 lên 11,113, thêm 273 cạnh so với lần trước.

## Ghi nhận thực thi lượt bổ sung 10.000 chuyến

Đã chạy đủ 10 cell code, 11 fixture kỹ thuật và 44 kiểm tra độc lập đều đạt. Chuyến mới được lấy trong đúng train; giữ nguyên vùng, graph, ngưỡng QA và các quan sát của lượt hoàn tất trước.

- Đợt 1: 5,000 chuyến, thêm 2,582 cạnh; thời gian matching của lượt này 0.8 phút, cache hit 274 batch.
- Đợt 2: 5,000 chuyến, thêm 433 cạnh; thời gian matching của lượt này 0.4 phút, cache hit 248 batch.
- Đợt 3: 5,000 chuyến, thêm 286 cạnh; thời gian matching của lượt này 0.5 phút, cache hit 244 batch.
- Đợt 4: 5,000 chuyến, thêm 134 cạnh; thời gian matching của lượt này 17.4 phút, cache hit 0 batch.
- Đợt 5: 5,000 chuyến, thêm 139 cạnh; thời gian matching của lượt này 12.6 phút, cache hit 0 batch.

Các đợt 1–3 dùng lại cache; thời gian trên không phải thời gian chạy mới toàn bộ 34,501 chuyến. Dữ liệu, config, phiên bản, runtime và kiểm chứng nằm trong thư mục kết quả mới nhất.

Khi đóng kernel trên Windows, Joblib in 10 `KeyError` từ `resource_tracker` khi dọn thư mục memmap tạm. Các lỗi này xuất hiện sau khi mọi cell đã hoàn tất; 0 cell lỗi và 44 kiểm tra đầu ra đều đạt. Nguyên nhân dọn file tạm chưa được xử lý trong lượt này; chi tiết ở `execution_notes.json`.
