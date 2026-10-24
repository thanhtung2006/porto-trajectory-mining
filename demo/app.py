"""Explore verified historical taxi slowdown profiles; no raw-data processing at runtime."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import gzip
import hashlib
import html
import json
import math

import folium
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

DATA_DIR = Path(__file__).resolve().parent / "data"
GROUP_LABELS = {
    "weekday": "Ngày trong tuần · Thứ 2–Thứ 6", "weekend": "Cuối tuần · Thứ 7–Chủ nhật",
    "0": "Thứ 2", "1": "Thứ 3", "2": "Thứ 4", "3": "Thứ 5", "4": "Thứ 6", "5": "Thứ 7", "6": "Chủ nhật",
}
MODE_LABELS = {"slowdown": "Các đoạn giảm tốc", "recurrent": "Các đoạn chậm lặp lại", "supported": "Tất cả đoạn đủ dữ liệu"}
COLORS = {"background": "#d9e0e5", "normal": "#16877e", "slowdown": "#ea7b28", "recurrent": "#8b3fad"}
ROAD_LABELS = {"motorway": "Cao tốc", "motorway_link": "Nhánh cao tốc", "trunk": "Trục lớn", "trunk_link": "Nhánh trục lớn",
               "primary": "Đường chính", "primary_link": "Nhánh đường chính", "secondary": "Đường cấp 2",
               "tertiary": "Đường cấp 3", "residential": "Đường khu dân cư", "unclassified": "Đường khác",
               "living_street": "Đường nội khu", "service": "Đường dịch vụ"}


@st.cache_data(show_spinner=False)
def load_snapshot(version: tuple):
    """The version includes file mtimes/sizes, so updated snapshots invalidate the cache."""
    metadata = json.loads((DATA_DIR / "metadata.json").read_text(encoding="utf-8"))
    if metadata["schema_version"] != 1:
        raise ValueError("Phiên bản snapshot chưa được hỗ trợ.")
    for name, specification in metadata["files"].items():
        path = DATA_DIR / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != specification["sha256"]:
            raise ValueError(f"Snapshot không khớp checksum: {name}. Hãy khôi phục hoặc xuất lại snapshot.")
    with gzip.open(DATA_DIR / "network.geojson.gz", "rt", encoding="utf-8") as handle:
        network = json.load(handle)
    edges = pd.read_parquet(DATA_DIR / "edges.parquet")
    profiles = pd.read_parquet(DATA_DIR / "profiles.parquet")
    clusters = pd.read_parquet(DATA_DIR / "recurrent_clusters.parquet")
    if len(edges) != metadata["n_edges"] or len(network["features"]) != len(edges):
        raise ValueError("Số cạnh trong bản đồ không khớp bảng thống kê.")
    if len(profiles) != metadata["n_profile_rows"] or profiles[["edge_index", "day_group", "slot"]].duplicated().any():
        raise ValueError("Profile bị thiếu hoặc trùng khóa cạnh–nhóm ngày–khung giờ.")
    return metadata, network, edges, profiles, clusters


def time_label(slot: int, width: int) -> str:
    start = int(slot) * width
    return f"{start:02d}:00–{start + width:02d}:00"


def select_view(edges, profiles, clusters, day_group, slot, mode):
    """Keep insufficient_data explicit; never convert missing speeds into free flow."""
    current = profiles[profiles.day_group.eq(day_group) & profiles.slot.eq(slot)].merge(edges, on="edge_index", validate="one_to_one")
    supported = current.status.ne("insufficient_data")
    if mode == "slowdown":
        visible = current[current.status.eq("slowdown")].copy()
    elif mode == "recurrent":
        visible = current[current.is_recurrent].copy()
    else:
        visible = current[supported].copy()
    active_clusters = clusters[clusters.day_group.eq(day_group) & clusters.slot.eq(slot)].copy()
    summary = {
        "supported": int(supported.sum()), "slowdown": int(current.status.eq("slowdown").sum()),
        "recurrent": int(current.is_recurrent.sum()), "total": len(current),
        "supported_length_fraction": float(current.loc[supported, "length_inside_m"].sum() / current.length_inside_m.sum()),
    }
    return current, visible, active_clusters, summary


def feature_color(row):
    if bool(row.is_recurrent): return COLORS["recurrent"]
    return COLORS["slowdown"] if row.status == "slowdown" else COLORS["normal"]


def format_frequency(row):
    eligible = int(row.eligible_days)
    return f"{int(row.slow_days)}/{eligible} ngày đủ dữ liệu ({float(row.slow_frequency):.0%})" if eligible else "Chưa có ngày đủ dữ liệu để xét lặp lại"


def visible_geojson(network, visible):
    features = []
    for row in visible.itertuples():
        properties = {
            "Mã đoạn": html.escape(str(row.edge_id)),
            "Loại đường": html.escape(ROAD_LABELS.get(str(row.road_class), str(row.road_class))),
            "Tốc độ lịch sử": f"{float(row.estimated_speed_kmh):.1f} km/h",
            "Tốc độ tham chiếu": f"{float(row.reference_speed_kmh):.1f} km/h",
            "So với tham chiếu": f"{float(row.speed_ratio):.0%}",
            "Chuyến / taxi / ngày": f"{int(row.n_trips)} / {int(row.n_taxis)} / {int(row.n_days)}",
            "Tần suất chậm": format_frequency(row),
            "_color": feature_color(row),
        }
        # Folium needs an explicit ID; otherwise it may generate invalid JS using
        # a Vietnamese tooltip field with spaces as feature.properties.<field>.
        features.append({"type": "Feature", "id": str(int(row.edge_index)),
                         "geometry": network["features"][int(row.edge_index)]["geometry"], "properties": properties})
    return {"type": "FeatureCollection", "features": features}


def cluster_geojson(network, clusters):
    features = []
    for row in clusters.itertuples():
        lines = []
        for index in row.edge_indices:
            geometry = network["features"][int(index)]["geometry"]
            if geometry["type"] == "LineString": lines.append(geometry["coordinates"])
            elif geometry["type"] == "MultiLineString": lines.extend(geometry["coordinates"])
        features.append({"type": "Feature", "id": str(row.cluster_id), "geometry": {"type": "MultiLineString", "coordinates": lines},
            "properties": {"Cụm": str(row.cluster_id), "Số đoạn": int(row.n_edges),
                           "Chiều dài": f"{float(row.length_m):.0f} m", "Tốc độ tương đối trung bình": f"{float(row.mean_speed_ratio):.0%}"}})
    return {"type": "FeatureCollection", "features": features}


def make_map(metadata, network, visible, clusters, basemap, show_clusters):
    west, south, east, north = metadata["bbox"]
    road_map = folium.Map(location=[(south+north)/2, (west+east)/2], zoom_start=13,
                          tiles=None, control_scale=True, prefer_canvas=True)
    if basemap:
        folium.TileLayer("OpenStreetMap",name="Nền OpenStreetMap",opacity=.55).add_to(road_map)
    folium.GeoJson(network, name="Mạng đường nền", style_function=lambda _: {"color": COLORS["background"], "weight": 1, "opacity": .8}).add_to(road_map)
    overlay = visible_geojson(network, visible)
    if overlay["features"]:
        fields = ["Mã đoạn", "Loại đường", "Tốc độ lịch sử", "Tốc độ tham chiếu", "So với tham chiếu", "Chuyến / taxi / ngày", "Tần suất chậm"]
        folium.GeoJson(overlay, name="Các đoạn đang xem",
            style_function=lambda feature: {"color": feature["properties"]["_color"], "weight": 3.5, "opacity": .95},
            highlight_function=lambda _: {"weight": 6, "opacity": 1},
            tooltip=folium.GeoJsonTooltip(fields=fields, aliases=[label+":" for label in fields], sticky=False, labels=True)).add_to(road_map)
    if show_clusters and not clusters.empty:
        folium.GeoJson(cluster_geojson(network, clusters), name="Cụm cạnh có mẫu chậm lặp lại",
            style_function=lambda _: {"color": COLORS["recurrent"], "weight": 6, "opacity": .45},
            tooltip=folium.GeoJsonTooltip(fields=["Cụm", "Số đoạn", "Chiều dài", "Tốc độ tương đối trung bình"], sticky=False)).add_to(road_map)
    folium.Rectangle([[south, west], [north, east]], color="#185c64", weight=1, fill=False, dash_array="5 6", tooltip="Ranh giới vùng nghiên cứu C 8×8 km").add_to(road_map)
    folium.LayerControl(collapsed=True).add_to(road_map)
    road_map.fit_bounds([[south, west], [north, east]])
    return road_map


def geometry_lines(geometry):
    return [geometry["coordinates"]] if geometry["type"] == "LineString" else geometry["coordinates"] if geometry["type"] == "MultiLineString" else []


def make_static_map(metadata, network, visible, label):
    fig, ax = plt.subplots(figsize=(9, 8))
    background = [line for feature in network["features"] for line in geometry_lines(feature["geometry"])]
    ax.add_collection(LineCollection(background, colors=COLORS["background"], linewidths=.45))
    lines, colors = [], []
    for row in visible.itertuples():
        for line in geometry_lines(network["features"][int(row.edge_index)]["geometry"]):
            lines.append(line); colors.append(feature_color(row))
    if lines: ax.add_collection(LineCollection(lines, colors=colors, linewidths=1.8))
    west, south, east, north = metadata["bbox"]
    ax.set(xlim=(west,east), ylim=(south,north), xlabel="Longitude", ylabel="Latitude", title=label)
    ax.set_aspect(1/math.cos(math.radians((south+north)/2)))
    ax.grid(alpha=.15);fig.tight_layout()
    return fig


def download_table(frame):
    result = frame[["edge_id", "road_class", "estimated_speed_kmh", "reference_speed_kmh", "speed_ratio",
        "n_trips", "n_taxis", "n_days", "eligible_days", "slow_days", "slow_frequency", "is_recurrent"]].copy()
    result.columns = ["Mã đoạn", "Loại đường", "Tốc độ lịch sử (km/h)", "Tham chiếu (km/h)", "Tỷ lệ tốc độ",
        "Số chuyến", "Số taxi", "Số ngày", "Ngày đủ dữ liệu", "Ngày chậm", "Tần suất chậm", "Chậm lặp lại"]
    return result


def main():
    st.set_page_config(page_title="Porto · Giảm tốc theo giờ", page_icon="🚕", layout="wide")
    st.title("Porto · Những đoạn đường thường chậm theo giờ")
    st.caption("Khám phá mẫu giảm tốc lịch sử từ GPS taxi trong vùng C 8×8 km.")
    try:
        names = ["metadata.json", "network.geojson.gz", "edges.parquet", "profiles.parquet", "recurrent_clusters.parquet"]
        version = tuple((name, (DATA_DIR/name).stat().st_mtime_ns, (DATA_DIR/name).stat().st_size) for name in names)
        metadata, network, edges, profiles, clusters = load_snapshot(version)
    except (FileNotFoundError, ValueError, KeyError) as error:
        st.error(f"Không mở được dữ liệu demo: {error}")
        st.info("Khôi phục demo/data từ repo, hoặc chạy python demo/export_snapshot.py sau khi hoàn tất notebook mô hình.")
        st.stop()
    width = int(metadata["hour_width"])
    groups = [str(value) for value in profiles.day_group.cat.categories]
    slots = sorted(int(value) for value in profiles.slot.unique())
    with st.sidebar:
        st.header("Chọn thời điểm")
        group = st.selectbox("Nhóm ngày", groups, format_func=lambda value: GROUP_LABELS.get(value,value), key="day_group")
        slot = st.selectbox("Khung giờ · Europe/Lisbon", slots, index=slots.index(8//width), format_func=lambda value: time_label(value,width), key="slot")
        mode = st.radio("Hiển thị", list(MODE_LABELS), format_func=MODE_LABELS.get, key="display_mode")
        show_clusters = st.checkbox("Tô nổi các cụm chậm lặp lại", value=True, key="show_clusters")
        basemap = st.checkbox("Hiển thị nền bản đồ", value=True, key="basemap")
        st.divider()
        st.markdown("**Dữ liệu lịch sử**")
        start=pd.Timestamp(metadata["train_start"]).strftime("%d/%m/%Y")
        end=(pd.Timestamp(metadata["train_end_exclusive"])-pd.Timedelta(seconds=1)).strftime("%d/%m/%Y")
        st.caption(f"{start} – {end}\n\n{metadata['n_edges']:,} cạnh có hướng trong vùng.")
        st.caption("Đường nền xám có thể thiếu dữ liệu hoặc đang bị ẩn bởi bộ lọc. Không xem đường xám là thông thoáng.")
    current, visible, active_clusters, summary = select_view(edges, profiles, clusters, group, slot, mode)
    title = f"{GROUP_LABELS.get(group,group)} · {time_label(slot,width)}"
    st.subheader(title)
    cards = st.columns(4)
    cards[0].metric("Đoạn đủ dữ liệu", f"{summary['supported']:,}", help=f"Trong tổng {summary['total']:,} cạnh có hướng của vùng.")
    cards[1].metric("Đoạn giảm tốc", f"{summary['slowdown']:,}", help="Đủ dữ liệu và tốc độ thấp hơn ngưỡng tham chiếu.")
    cards[2].metric("Đoạn chậm lặp lại", f"{summary['recurrent']:,}", help="Tần suất được tính trên ngày đủ dữ liệu, không đếm ngày thiếu thành ngày thông thoáng.")
    cards[3].metric("Độ phủ theo chiều dài", f"{summary['supported_length_fraction']:.1%}", help="Chiều dài cạnh có hướng đủ support / tổng chiều dài cạnh có hướng trong vùng.")
    legend="　".join(f'<span style="white-space:nowrap"><span style="display:inline-block;width:11px;height:11px;border-radius:50%;background:{color};margin-right:6px"></span>{label}</span>'
        for color,label in [(COLORS["slowdown"],"Giảm tốc"),(COLORS["recurrent"],"Chậm lặp lại"),
                            (COLORS["normal"],"Không giảm tốc tương đối"),(COLORS["background"],"Mạng đường nền")])
    st.markdown(legend,unsafe_allow_html=True)
    st.caption(f"Đang tô {len(visible):,} đoạn theo bộ lọc; {len(active_clusters):,} cụm cạnh có mẫu chậm lặp lại. Di chuột lên đường màu để xem số liệu.")
    if visible.empty:
        st.info("Không có đoạn đáp ứng bộ lọc ở thời điểm này. Thử khung giờ khác hoặc chọn tất cả đoạn đủ dữ liệu.")
    road_map = make_map(metadata, network, visible, active_clusters, basemap, show_clusters)
    interactive, static = st.tabs(["Bản đồ tương tác", "Ảnh tĩnh"])
    with interactive:
        st_folium(road_map, height=620, use_container_width=True, returned_objects=[], key=f"map_{group}_{slot}_{mode}_{basemap}_{show_clusters}")
    with static:
        figure = make_static_map(metadata, network, visible, title)
        st.pyplot(figure, clear_figure=False)
        image = BytesIO();figure.savefig(image,format="png",dpi=140,bbox_inches="tight");plt.close(figure)
        st.download_button("Tải ảnh PNG", image.getvalue(), file_name=f"porto_{group}_{slot:02d}.png", mime="image/png")
        st.caption("Ảnh tĩnh không cần tải nền bản đồ hoặc JavaScript từ Internet.")
    first, second = st.columns(2)
    first.download_button("Tải bản đồ HTML", road_map.get_root().render(), file_name=f"porto_{group}_{slot:02d}.html", mime="text/html")
    first.caption("HTML có các lớp và tooltip; cần Internet cho thư viện bản đồ và nền trực tuyến.")
    second.download_button("Tải bảng đang xem · CSV", download_table(visible).to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"porto_{group}_{slot:02d}.csv", mime="text/csv")
    with st.expander("Đọc kết quả như thế nào?", expanded=False):
        ratio=float(metadata["slowdown_ratio_threshold"])
        st.markdown(f"""
**Giảm tốc:** tốc độ lịch sử dưới **{ratio:.0%} tốc độ tham chiếu** (giảm trên {1-ratio:.0%}),
với ít nhất **{metadata['min_trips']} chuyến, {metadata['min_taxis']} taxi và {metadata['min_days']} ngày**.

**Lặp lại:** chậm trong ít nhất {metadata['min_recurrent_frequency']:.0%} số ngày đủ dữ liệu,
và có ít nhất {metadata['min_days']} ngày đủ dữ liệu. Cụm nối các cạnh theo topology và hướng di chuyển.

Tốc độ tham chiếu lấy từ P85 tốc độ trong train, dùng làm mốc so sánh.

Nhóm ngày trong tuần gộp Thứ 2–Thứ 6; chưa xem riêng một thứ cụ thể ở snapshot này.
Đây là mẫu từ taxi lịch sử, không phải giao thông trực tiếp. Taxi dừng/chờ cũng có thể tạo tín hiệu chậm;
chưa có nhãn ùn tắc độc lập để xác nhận nguyên nhân.
""")
    with st.expander("So sánh các khung giờ của nhóm ngày đang chọn"):
        subset=profiles[profiles.day_group.eq(group)]
        overview=subset.assign(slow=subset.status.eq("slowdown")).groupby("slot",observed=True).agg(
            **{"Giảm tốc":("slow","sum"),"Chậm lặp lại":("is_recurrent","sum")})
        overview.index=[f"{int(value)*width:02d}:00" for value in overview.index]
        st.line_chart(overview)
        st.caption("Số đoạn đủ điều kiện theo từng khung giờ; không phải số xe hay lượng xe đồng thời trên đường.")
    with st.expander("Chi tiết các đoạn đang hiển thị"):
        ordered=visible.sort_values(["is_recurrent","slow_frequency","n_days","speed_ratio"],ascending=[False,False,False,True])
        st.dataframe(download_table(ordered.head(300)),hide_index=True,width="stretch")
        st.caption("Hiển thị tối đa 300 dòng; tải CSV để lấy toàn bộ các đoạn theo bộ lọc.")
    with st.expander("Kiểm chứng mô hình ETA offline"):
        metrics=pd.DataFrame(metadata["metrics"])[["method","MAE_s","RMSE_s","median_AE_s","WAPE"]].copy()
        metrics.columns=["Phương pháp","MAE (s)","RMSE (s)","Median AE (s)","WAPE"]
        metrics["WAPE"]=metrics["WAPE"].map(lambda value:f"{value:.1%}")
        st.dataframe(metrics.round(3),hide_index=True,width="stretch")
        coverage=metadata["evaluation_coverage"]
        st.caption(f"Cùng {coverage['common_evaluated_routes']:,} đoạn QA thuộc {coverage['evaluated_test_trips']:,}/{coverage['selected_complete_source_test_trips']:,} chuyến test đã chọn ({coverage['evaluated_fraction_all_selected']:.0%}). Sai số áp dụng cho chính đoạn giữ lại; chưa đo lợi ích tuyến thay thế.")
    st.caption("Nguồn: Porto Taxi ECML/PKDD 2015 · Mạng đường © OpenStreetMap contributors · Chỉ dùng cho khảo sát lịch sử.")


if __name__ == "__main__":
    main()
