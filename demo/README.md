# Demo giảm tốc taxi Porto theo giờ

Chọn **ngày trong tuần/cuối tuần** và **khung 1 giờ**, xem các đoạn giảm tốc, mẫu chậm lặp lại,
tooltip tốc độ và số chuyến/taxi/ngày. Có ảnh tĩnh, bảng chi tiết và tải HTML/PNG/CSV.
Demo dùng kết quả đã tính; không tải OSM, không đọc `train.csv`, không matching/train khi mở app.

## Chạy từ thư mục gốc repo

Khuyến nghị Python 3.11–3.13. Môi trường đã kiểm chứng tại workspace là Python 3.13.

```powershell
python -m pip install -r demo/requirements.txt
python -m streamlit run demo/app.py
```

Mở địa chỉ Streamlit in ra, thường là `http://localhost:8501`. Dừng bằng Ctrl+C.
App cũng chạy được khi gọi script bằng đường dẫn tuyệt đối vì dữ liệu tính theo vị trí `app.py`.
Không cần cài môi trường đầy đủ của notebook nếu chỉ xem demo với snapshot có sẵn.

## Cách xem

1. Chọn nhóm ngày và giờ ở thanh bên. Giờ là **Europe/Lisbon**, dùng thời gian điểm GPS.
2. Chọn các đoạn giảm tốc, chậm lặp lại hoặc tất cả đoạn đủ dữ liệu.
3. Di chuột lên đường màu: xem tốc độ lịch sử/tham chiếu, tỷ lệ tốc độ, chuyến/taxi/ngày và số ngày chậm.
4. Bật lớp cụm để xem các cạnh có mẫu chậm lặp lại nối nhau theo topology.
5. Nếu nền bản đồ không tải được, bỏ chọn nền hoặc mở tab **Ảnh tĩnh**.

Cam = giảm tốc; tím = chậm lặp lại; xanh = đủ dữ liệu và không giảm tốc tương đối theo ngưỡng.
Đường nền xám có thể thiếu dữ liệu hoặc bị ẩn bởi bộ lọc; không đồng nghĩa thông thoáng.
Nhóm weekday gộp Thứ 2–Thứ 6, weekend gộp Thứ 7–Chủ nhật, chưa phân biệt riêng một thứ.

Snapshot hiện tại dùng ngưỡng `speed / reference_speed < 0.6`: tốc độ dưới 60% tham chiếu,
tương đương giảm trên 40%. Cần ≥3 chuyến, ≥3 taxi, ≥3 ngày cho profile lịch sử.
Tần suất lặp lại chỉ đếm ngày đủ dữ liệu; không tính ngày thiếu thành ngày thông thoáng.

## Dữ liệu nào đưa lên Git?

**Giữ `demo/data/` trong repo.** Đây là snapshot tổng hợp khoảng 4,1 MB, gồm:

- `network.geojson.gz`: hình học cạnh đường trong vùng, đơn giản hóa 2 m chỉ để hiển thị.
- `edges.parquet`: mã cạnh, loại đường, chiều dài trong vùng.
- `profiles.parquet`: thống kê cạnh × nhóm ngày × khung giờ, support và trạng thái.
- `recurrent_clusters.parquet`: cụm các cạnh có mẫu chậm lặp lại theo giờ.
- `metadata.json`: tham số nghiên cứu, nguồn, checksum và metrics đã kiểm chứng.

Snapshot không chứa GPS thô, `TRIP_ID` hoặc `TAXI_ID`. Không cần push `data/`, `cache/` và `outputs/` ở gốc repo.
Các bảng thống kê này mô tả mẫu taxi train đã chọn; không đại diện mọi xe trong Porto.

Muốn cập nhật snapshot sau khi chạy notebook mô hình, dùng môi trường notebook có GeoPandas/pyproj:

```powershell
python demo/export_snapshot.py
```

Hoặc chỉ định lượt đã hoàn tất:

```powershell
python demo/export_snapshot.py --model-run outputs/region_modeling/c01cada311f38e85a9d4
```

Exporter chỉ chấp nhận đầu ra có kiểm chứng độc lập đạt. Clone mới thiếu outputs vẫn xem được
snapshot đã đưa lên Git; chỉ việc cập nhật snapshot mới cần các nguồn pipeline cục bộ.

## Phạm vi và giới hạn

Demo này để xem mẫu giảm tốc theo thời gian, **chưa có chọn A/B và tìm tuyến thay thế**.
Mạng hiện tại có thể khác GPS 2013; thời gian trên cạnh ngắn là nội suy từ GPS 15 giây.
Taxi dừng/chờ có thể tạo tín hiệu chậm, chưa có ground truth ùn tắc. Không dùng bản đồ như live traffic.
Các cụm lịch sử gộp cạnh có mẫu lặp lại theo khung giờ; chưa chứng minh chúng đồng thời chậm trong mọi ngày.

Folium tương tác cần Internet cho JS/CSS CDN và nền bản đồ; tab ảnh tĩnh hoạt động bằng dữ liệu cục bộ.
Tệp HTML tải về vẫn cần các tài nguyên bản đồ trực tuyến, không phải bản đồ offline hoàn toàn.

Nguồn kỹ thuật: [Streamlit](https://docs.streamlit.io/),
[streamlit-folium](https://github.com/randyzwitch/streamlit-folium),
[Folium GeoJSON](https://python-visualization.github.io/folium/latest/user_guide/geojson/geojson_popup_and_tooltip.html).

## Đã kiểm chứng tại workspace

- Snapshot thật: 15.882 cạnh, 762.336 profile, khoảng 4,1 MB; kiểm tra checksum khi mở.
- Bốn trường hợp điều khiển Streamlit: đổi nhóm ngày, giờ, chế độ xem và tắt nền/lớp cụm đều đạt;
  các số trên giao diện được đối chiếu trực tiếp với bảng snapshot.
- Trình duyệt Chrome headless: bản đồ mặc định và cuối tuần 17–18 giờ đều render, có nền OSM,
  không có lỗi JavaScript. Ảnh xem trước là ảnh chụp app thật.
- Thư mục dữ liệu gốc/cache/outputs/PDF được Git bỏ qua; snapshot `demo/data/` được phép đưa lên Git.
- Năm notebook đã kiểm tra cú pháp và nhận đúng gốc repo từ thư mục gốc hoặc thư mục notebook.
  Không chạy lại matching/train chỉ vì sắp xếp file.
