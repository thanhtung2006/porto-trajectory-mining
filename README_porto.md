# Chạy notebook Porto

Mở `porto_trajectory_mining.ipynb` bằng JupyterLab hoặc VS Code và chọn Python kernel đã cài dependencies.
Mọi hàm xử lý nằm trong notebook. Không có web/API/demo định tuyến.

## Chạy smoke test

1. Cài `requirements_porto.txt` bằng `python -m pip install -r requirements_porto.txt`, hoặc dùng cell cài đặt trong notebook.
2. Đặt `train.csv` đầy đủ của [cuộc thi Kaggle](https://www.kaggle.com/competitions/pkdd-15-predict-taxi-service-trajectory-i/data) vào `data/`.
   Có thể giữ ZIP chứa `train.csv` rồi sửa `CFG['data_path']`; notebook không yêu cầu thông tin xác thực Kaggle.
3. Trong cell cấu hình đầu tiên, giữ `mode='smoke_test'`, số chuyến 300. Kiểm tra `root`, `data_path`, `bbox`,
   `study_start`, `train_end`, `validation_end`, `study_end`.
4. Restart kernel và Run All. Xem QA trước khi diễn giải profile. Smoke test không đủ để kết luận giao thông.

Mặc định phân tích corridor để giảm bất định nội suy ở GPS 15 giây. Đặt `analysis_unit='edge'` để so sánh ở mức cạnh;
các bảng luôn lưu cạnh gốc và nguồn thống kê. Giữ cùng mức phân tích khi so sánh các phương pháp.

## Chạy experiment

Đặt `mode='experiment'`; mặc định 20.000 chuyến, điều chỉnh `max_trips['experiment']` trong khoảng 10.000–30.000 trước.
Lấy mẫu trải theo ngày bằng seed, không lấy head(N). Tăng mẫu sau khi xem runtime, matching QA và coverage.
Chỉ tune bằng validation; giữ kín giai đoạn test. Nếu đổi khoảng nghiên cứu, sửa cả ba ranh giới split.

`run_m2=False` bỏ hồi quy bổ sung trong thực nghiệm; các kiểm thử kỹ thuật nhỏ vẫn kiểm tra hàm M2.
`cpu_threads` giới hạn thư viện CPU. `force_rematch=True` yêu cầu tính lại matching;
cache tự phân biệt data SHA, graph, code, backend/version và cấu hình.

## Kết quả và cache

- `outputs/latest_run.json`: trỏ tới thư mục kết quả lần chạy mới nhất, kèm trạng thái từng bước.
- `outputs/<config_hash>_<UTC_run_time>/`: config, package versions, runtime/RSS, split/filter audit,
  QA matching, traversals, statistics, mining, coverage, sensitivity, models, test predictions/metrics và hình khi có dữ liệu.
- `cache/graphs/`: GraphML, metadata và ánh xạ cạnh; lần sau tải từ cache.
- `cache/matching/`: checkpoint Parquet theo batch, tái sử dụng sau khi restart.

Mỗi lần chạy có thư mục output riêng để tránh trộn kết quả cũ với lần chạy bị thiếu dữ liệu.
Khóa không có trong bảng ngày dạng sparse nghĩa là thiếu dữ liệu; profile lịch sử ghi `insufficient_data` rõ ràng.

## Đã xác minh khi bàn giao

- Đọc hai PDF thực sự có trong workspace: Overview 41 trang và pipeline Porto 12 trang.
- Kiểm tra cú pháp tất cả code cells và định dạng notebook; chạy notebook bằng kernel Jupyter.
- Tải, chiếu và lưu road graph OSM thật: 23.732 cạnh có hướng cho vùng cấu hình mặc định.
- Chạy kiểm thử kỹ thuật trong mục 12, gồm timestamp gốc, partial distance, split chuyến, UTC/DST,
  ETA qua nhiều giờ, HMM, traversal quay lại cạnh, support, recurrence, M2 và bốn phương pháp.
- Chạy kiểm tra tích hợp trên **fixture tổng hợp, không phải Porto**: CSV/ZIP, cache đọc lại,
  làm sạch, matching, train/validation, mining, M2, test cùng route và xuất artifacts.
  Báo cáo kỹ thuật: `outputs/integration_verification.json`; không lưu metrics fixture như benchmark Porto.

**Đã chạy smoke test trên GPS Porto thật ngày 21/10/2026:** lấy 300 chuyến trải qua 56 ngày từ `data/train.csv`.
Toàn bộ notebook đã chạy xong, gồm matching, train/validation, M2, mining và đánh giá offline.
Các kiểm thử kỹ thuật có 30 passed. Xem thư mục được trỏ bởi `outputs/latest_run.json`.

**Metric nằm ở mục 10 của notebook**, đồng thời được lưu trong `eta_metrics.csv` và `eta_metrics.parquet`.
MAE, RMSE và median absolute error có đơn vị giây; WAPE là tổng sai số tuyệt đối chia tổng thời lượng thật.
Tất cả các chỉ số này càng thấp càng tốt. Không sử dụng Accuracy/F1 cho ùn tắc khi không có nhãn độc lập.

Lần smoke test này đánh giá được 29 đoạn liên tục thuộc 25/35 chuyến test được chọn (71,4% chuyến;
53,3% tổng thời lượng test gốc). MAE: B0 136,2s, B1 107,4s, M1 107,4s, M2 76,8s.
Tất cả route test thuộc nhóm phải fallback; mẫu còn thưa nên M1 chưa cải thiện B1, không có cạnh–giờ
đủ support để kết luận giảm tốc hay vẽ heatmap tốc độ đáng tin. Đây là kiểm tra kỹ thuật trên dữ liệu thật,
chưa thay thế experiment 10.000–30.000 chuyến và chưa xác nhận ùn tắc thật.

`fastmm` không có wheel phù hợp cho Python 3.13 Windows trong lần cài kiểm tra. Notebook có adapter dựa trên API
chính thức 0.3.2 nhưng adapter này **chưa được thực thi** tại đây. HMM Leuven 1.1.4 đã chạy kiểm thử thực tế.
Muốn ưu tiên fastmm, dùng Python 3.11/3.12 phù hợp và cài thêm `fastmm==0.3.2`; notebook tự kiểm tra API.
Road graph hiện tại khác thời kỳ GPS 2013; kết quả matching vẫn cần xem hình và đánh giá thủ công.

Danh sách nguồn, đối chiếu lý thuyết và các thay đổi so với PDF nằm ngay trong notebook.
