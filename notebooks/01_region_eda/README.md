> Notebook cùng thư mục: [porto_region_eda.ipynb](porto_region_eda.ipynb). [Về trang chủ repo](../../README.md).

> Các đường dẫn `data/`, `cache/`, `outputs/` trong tài liệu đều tính từ thư mục gốc repo. Notebook tự tìm thư mục gốc dù mở từ thư mục con. Các lệnh terminal trong README chạy từ gốc repo.

# Khảo sát vùng Porto bằng GPS

Mở `porto_region_eda.ipynb`. Đây là notebook riêng; `porto_trajectory_mining.ipynb` được giữ nguyên.
Notebook mới không tải road graph, không đếm cạnh, không map matching và không chạy mô hình.

## 1. Sửa đường dẫn

Trong **cell A — Cấu hình**, sửa `CFG['data_path']` nếu dữ liệu không ở `data/train.csv`.
Chấp nhận CSV hoặc ZIP chứa `train.csv`; dùng `zip_member` nếu ZIP có nhiều CSV phù hợp.
Hỗ trợ tên cột `DAY_TYPE` của file hiện tại và alias `DAYTYPE`, không dùng trường này suy ra ngày làm việc.

## 2. Chạy lần đầu

Chọn kernel Python đã cài dependencies rồi **Restart Kernel → Run All**.
Cài package thiếu bằng cell B hoặc `python -m pip install -r requirements/requirements_region_eda.txt`.

Mặc định đọc cấu hình notebook cũ để dùng giai đoạn train: **01/07/2013 đến trước 05/08/2013 theo Lisbon**.
Lấy **10.000 chuyến**, 35% bắt đầu cao điểm sáng, 35% chiều, 30% ngoài cao điểm; phân bổ qua các ngày.
Các khung 07–09h và 16–19h là giả định lấy mẫu, không phải giờ cao điểm đã được chứng minh.
Bạn có thể sửa ngày, số chuyến, seed và tỷ lệ ở A. Khi đổi các tham số này, nên Run All.

Kết quả mới nhất được trỏ bởi `outputs/region_eda/latest_run.json`.
Mỗi lần Run All có thư mục output riêng; cache được tái sử dụng.

## 3. Xem bản đồ để tự tìm vùng

Trong thư mục `maps/` của lần chạy mới nhất, mở HTML bằng trình duyệt:

- `01_grid_distinct_trips.html`: số chuyến khác nhau có GPS trong từng ô.
- `02_morning_peak.html`, `03_evening_peak.html`, `04_off_peak.html`: so sánh độ phủ theo nhóm giờ của **điểm GPS**.
- `05_observed_days.html`: số ngày có GPS mẫu trong ô.
- `06_trip_endpoints.html`: đầu/cuối chuyến gốc, tách khỏi bản đồ toàn quỹ đạo.
- `07_sample_trajectories.html`: một số vệt GPS minh họa, không nối qua khoảng gián đoạn.

Di chuột lên ô để xem cell_id, ranh giới west/south/east/north, số trip/taxi/day và các nhóm giờ.
Click bản đồ để đọc tọa độ. Màu là độ phủ/mật độ **quan sát mẫu**, không phải tốc độ hay ùn tắc.
Mẫu 70/30 không phản ánh trực tiếp tỷ trọng nhu cầu toàn thành phố; xem metadata_all/study để biết phân bố gốc.

HTML không cần Python/server khi mở, nhưng JavaScript/CSS CDN và tiles nền cần mạng khi chưa cache.
Nếu nền không hoạt động, dùng PNG trong `figures/`: có cả toàn phạm vi và bản `_porto_view.png`.
Khung nhìn Porto chỉ là phóng to hiển thị, không loại GPS đi xa hoặc quyết định vùng thay bạn.

Muốn heatmap một ô: nhập cell_id ở **H1**, chạy lại **H1 và H2**. Không nhập thì notebook bỏ qua heatmap ô.

## 4. Nhập bounding box

Ở **cell R1**, thay `REGIONS=CFG['regions']` bằng danh sách của bạn:

```python
REGIONS = [
    {"name": "ten_vung", "bbox": [west, south, east, north]},
]
```

Thay west/south/east/north bằng số tọa độ thật; có thể nhập nhiều vùng, tên khác nhau.
Mặc định danh sách rỗng, EDA chung vẫn chạy xong. Notebook không tự chọn vùng cuối cùng.
Bạn cũng có thể nhập danh sách tại `CFG['regions']` ở cell A và giữ nguyên dòng mặc định ở R1.

## 5. Chạy lại khi đổi vùng

Giữ kernel đang chạy rồi chạy **R1 → R2**. Không cần đọc lại CSV, lấy mẫu hoặc tạo lưới.
Xem `outputs/csv/region_eda/<run_id>/regions/<region_key>/comparison.csv` và các bảng CSV thời gian/phân bố ô cùng thư mục.
Các bảng Parquet và các phần GPS trong vùng vẫn ở `regions/<region_key>/` của lần chạy.
`latest_regions.json` ghi bbox thực tế đã nhập; `08_regions_overlay.html` vẽ các ranh giới đó.

`n_trips_points_inside` là số chuyến có GPS thực trong vùng. `n_trips_chord_only` là các chuyến chỉ có
đường nối hai GPS liên tiếp cắt vùng, được ghi riêng là nội suy hình học. `n_trips_any_evidence` là hợp của hai tập.
Số chuyến toàn vùng được đếm distinct, không cộng số chuyến của các ô.

Đổi kích thước ô: sửa `grid_size_m` ở A, chạy A → F → G → R1 → R2.
Hoặc Restart/Run All: mẫu và GPS vẫn lấy từ cache. Cache metadata/mẫu/GPS tách khỏi grid/vùng.

## 6. Đã thực thi và giới hạn xác minh

- Đã kiểm tra định dạng/cú pháp và chạy toàn notebook trên dữ liệu thật.
- Metadata toàn file: **1.710.670 dòng**. EDA nghiên cứu dùng giai đoạn train cũ; GPS chi tiết chỉ trên mẫu.
- Đã chọn **10.000 chuyến qua 35 ngày**, đúng quota 3.500 sáng / 3.500 chiều / 3.000 ngoài cao điểm.
- Sau lọc GPS: **9.793 chuyến, 487.590 điểm**, tạo **3.516 ô 500m có GPS mẫu**. Ô không phải cạnh đường.
- Đã xuất 7 HTML, PNG, Parquet/CSV, báo cáo làm sạch, quota, runtime và metadata phạm vi.
- **26 kiểm thử logic passed**: timestamp, DST, distinct count, quota, CSV/ZIP và lọc/ra-vào vùng.
- Kiểm tra tích hợp trên fixture tổng hợp đã chạy cả vùng có dữ liệu, vùng trống, heatmap và đổi grid/vùng
  khi chặn mọi thao tác đọc CSV. Fixture được ghi rõ, không trình bày như kết quả Porto.
- Chưa có bbox hoặc cell_id do bạn chọn, nên **chưa xuất phân tích vùng/heatmap ô thực tế do bạn yêu cầu cụ thể**.
  Hàm tương ứng đã được kiểm thử, danh sách mặc định được giữ rỗng.
- Đã kiểm tra xuất HTML và PNG; chưa kiểm thử tương tác trực tiếp trong trình duyệt của bạn hoặc tiles khi offline.
- Không ước lượng số cạnh đường hoặc chọn vùng cuối. Mốc 5.000–7.000 cạnh phải kiểm tra ở giai đoạn road graph sau.

Chi tiết xác minh: `outputs/region_eda/notebook_verification.json`, `integration_verification.json`,
và `outputs/csv/region_eda/<run_id>/logic_tests.csv`. Notebook lưu phiên bản thư viện và nguồn tham khảo chính thức.

## 7. Nơi lưu CSV

Toàn bộ CSV được gom vào `outputs/csv/`, phân theo notebook, lần chạy và loại kết quả:

```text
outputs/
├── csv/
│   └── region_eda/<run_id>/
│       ├── grid_cells.csv
│       ├── metadata_*.csv
│       ├── candidate_regions/     # các bảng so sánh vùng ứng viên
│       └── regions/<region_key>/ # các bảng của vùng nhập ở R1
└── region_eda/<run_id>/
    ├── maps/                     # HTML
    ├── figures/                  # PNG
    ├── candidate_regions/        # bản đồ và báo cáo vùng ứng viên
    └── *.parquet                 # bảng dùng để xử lý tiếp
```

Cell **B1 — Bố trí kết quả CSV** định tuyến nơi xuất bảng, không đổi khóa cache xử lý dữ liệu.
Nếu kernel đang mở từ trước khi sửa notebook, chạy cell B1 trước khi xuất lại bảng hoặc chạy R1/R2.
