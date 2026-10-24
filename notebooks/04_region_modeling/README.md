> Notebook cùng thư mục: [porto_region_modeling.ipynb](porto_region_modeling.ipynb). [Về trang chủ repo](../../README.md).

> Các đường dẫn `data/`, `cache/`, `outputs/` trong tài liệu đều tính từ thư mục gốc repo. Notebook tự tìm thư mục gốc dù mở từ thư mục con. Các lệnh terminal trong README chạy từ gốc repo.

# Mô hình tốc độ và đánh giá offline vùng C 8×8 km

Mở `porto_region_modeling.ipynb`. Notebook mới dùng lại matching train của 34.501 chuyến
đã chọn, loại toàn bộ chuyến đi qua ranh giới kết thúc train, rồi lấy mẫu metadata độc lập
2.000 chuyến validation và 2.000 chuyến test từ `train.csv`. Không cần competition `test.csv`.

## Cách chạy

1. Cài nếu cần: `python -m pip install -r requirements/requirements_region_modeling.txt`.
2. Giữ dữ liệu và các cache/output nguồn đã có; chúng không được đưa lên Git.
3. Sửa đường dẫn ở **cell A**: `data_path`, `metadata_db`, `train_run`. Đường dẫn nguồn train
   mặc định trỏ đến lượt coverage `a3bc4981c0524eb0f19f` đã hoàn tất.
4. Giữ `mode='experiment'`, Restart Kernel → Run All. `smoke_test` chỉ dùng 150 chuyến
   mỗi holdout và chưa đủ để kết luận giao thông. `run_m2=False` bỏ hồi quy bổ sung.
5. Giảm `matching_workers` nếu máy ít RAM; `cpu_threads` giới hạn luồng thư viện số.

Train: 01/07 đến trước 05/08/2013; validation: 05/08 đến trước 19/08;
test: 19/08 đến trước 26/08, theo Europe/Lisbon. Train chọn để tăng coverage có thiên lệch;
holdout chọn phân tầng ngày × giờ, không dùng tốc độ/cạnh thiếu/QA để chọn chuyến.

## Các phương pháp

- B0: tốc độ P85 train theo cạnh, proxy thông thoáng, fallback loại đường/toàn train.
- B1: median giây/mét của cạnh, không xét giờ, có fallback.
- M1: median giây/mét theo cạnh × nhóm ngày × giờ, thử 1/2/4 giờ và mức support trên validation.
- M2: HistGradientBoostingRegressor CPU học log(giây/mét), encoder chỉ fit train, không dùng
  thời gian/tốc độ quan sát của chuyến dự đoán làm feature.

So sánh MAE, RMSE, median absolute error và WAPE trên cùng các đoạn test QA giữ lại.
Luôn công bố cả số trip, số route, tỷ lệ test được đánh giá và kết quả đủ support/fallback.
Không có nhãn ùn tắc độc lập; không dùng Accuracy/F1 và không bảo đảm M1/M2 thắng baseline.

## Kết quả

- `outputs/region_modeling/latest_run.json`: con trỏ chỉ được ghi sau khi notebook hoàn tất.
- `outputs/region_modeling/<run_key>/eta_metrics.parquet`: bảng sai số ETA.
- `evaluation_coverage.json`: mẫu số/tỷ lệ test và phạm vi đoạn được đánh giá.
- `selected_spec.json`: cấu hình chốt trước khi mở test để matching/đánh giá.
- `history_*.parquet`, `reference_*.parquet`, model Joblib: chỉ được fit trên train.
- `edge_daily_slowdown.parquet`, `edge_historical_slowdown.parquet`, cụm GeoJSON,
  `slowdown_sensitivity`, `train_taxi_consistency`: kết quả khai phá và độ tin cậy.
- `edge_time_profiles_for_future_demo.parquet`: profile có fallback, nguồn và support để
  tái sử dụng ở giai đoạn demo; notebook hiện tại không xây routing/web/API.
- `figures/`: phân bố train, coverage, heatmap cạnh đủ dữ liệu, ETA và ví dụ matching đạt/không đạt.
- CSV nhỏ tập trung tại `outputs/csv/region_modeling/<run_key>/`; bảng lớn giữ dạng Parquet.

Cache holdout GPS, matching theo batch và tổng hợp train độc lập với việc chọn hyperparameters.
Đổi nguồn, vùng, graph, seed hay QA tạo cache tương ứng; không cần matching lại train.
Một số cạnh có ít nhất một quan sát vẫn thiếu dữ liệu trong nhiều giờ. Thời gian cạnh là
nội suy từ GPS 15 giây, graph hiện tại có thể khác năm 2013 và dừng đón/trả khách có thể
gây giảm tốc. Các bảng mô tả mẫu taxi lịch sử đã chọn, không phải trạng thái giao thông toàn thành phố.

## Kết quả thực thi trên dữ liệu Porto thật

Lượt hoàn tất: `outputs/region_modeling/c01cada311f38e85a9d4`. Đã chạy đủ 11 cell code, 22 kiểm tra preflight, 17 kiểm tra trong notebook và 42 kiểm tra độc lập đều đạt.

Train còn 34,500/34,501 chuyến đã chọn sau khi loại toàn bộ 1 chuyến vượt ranh giới split. Matching train và các notebook cũ giữ nguyên từng byte. Validation/test mỗi tập chọn 2.000 chuyến mới độc lập.

M1 được chọn trên validation: 1 giờ, `weekday_weekend`, tối thiểu 3 chuyến. Ngưỡng giảm tốc 0.6; lý do chọn: `validation_taxi_consistency_of_derived_states_only`.

| Phương pháp | MAE (s) | RMSE (s) | Median AE (s) | WAPE |
|---|---:|---:|---:|---:|
| B0 | 195.95 | 297.09 | 148.75 | 46.54% |
| B1 | 106.44 | 227.41 | 54.31 | 25.28% |
| M1 | 92.62 | 214.62 | 49.89 | 22.00% |
| M2 | 119.50 | 237.20 | 70.75 | 28.38% |

Cùng cohort 1,543 route liên tục thuộc 1,320/2,000 chuyến test (66.0% tổng mẫu đã chọn; 69.1% chuyến có GPS sạch trong vùng). Giữ lại 47.0% tổng thời lượng chuyến test gốc đã chọn; mẫu số này gồm cả phần ngoài vùng/bị loại. Sai số chỉ so với thời lượng chính đoạn được giữ lại, không giả là ETA toàn chuyến.

- M1: MAE chênh -13.82s so với baseline tốt nhất; cải thiện trên cohort này, chưa chứng minh lợi ích định tuyến.
- M2: MAE chênh +13.06s so với baseline tốt nhất; chưa cải thiện trên cohort này.

Các sai số được chia theo nhóm đủ profile và phải fallback trong `eta_metrics.parquet`. Không có Accuracy/F1 hay nhãn ùn tắc độc lập.

Trong nhóm đủ profile, MAE B1/M1 = 103.40/81.67s; nhóm fallback = 110.66/107.82s. Điều này cho thấy lợi ích của M1 trong lượt này tập trung ở route có profile theo giờ đủ support. Các nhóm chia theo route; một trip có nhiều route có thể xuất hiện ở cả hai nhóm.

M2 chỉ dùng 99,940 mẫu train theo giới hạn CPU, với feature thời gian, hình học và loại đường. Giới hạn số mẫu, feature chưa mô tả đầy đủ khác biệt từng cạnh và giả định thời gian nội suy là các khả năng cần kiểm chứng cho kết quả kém hơn; chưa xác định nguyên nhân nhân quả. Không điều chỉnh mô hình theo kết quả test trong lượt này.


**Đọc các ca sai số lớn của lượt này:** ba ví dụ có quãng đường 61.9–542.5 m nhưng thời lượng 37.5–44.8 phút; cả ba có `fine_support_fraction=0`. Đây là các đoạn trung bình rất chậm và phải fallback; profile lịch sử không dự đoán được đầy đủ các khoảng dừng/chờ kéo dài này. Cần kiểm tra GPS để phân biệt dừng taxi với giảm tốc giao thông, chưa gán nguyên nhân ùn tắc. Các trường hợp này giúp giải thích đuôi sai số lớn và RMSE cao hơn nhiều so với MAE.

Khi đóng kernel, Joblib in 4 `KeyError` từ `resource_tracker` khi dọn thư mục memmap tạm trên Windows. Các cell và kiểm tra đầu ra đều hoàn tất; nguyên nhân thông báo dọn file tạm chưa được xử lý, được ghi trong `execution_notes.json`.
