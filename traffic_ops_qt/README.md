# NexusTrafficOps — PySide6 + QML

Bản chuyển đổi từ dashboard React (`traffic_management_dashboard.tsx`) sang Qt Quick.
Python giữ dữ liệu và mô phỏng, QML chỉ vẽ giao diện.

## Chạy

```bash
pip install -r requirements.txt
python main.py
```

Cần Python 3.9+ và PySide6 6.6 trở lên (đã chạy thử với 6.12).

## Cấu trúc

```
main.py            khởi tạo QGuiApplication, nạp QML, đăng ký image provider
backend.py         TrafficBackend (QML_ELEMENT): telemetry, timer, sinh cảnh báo
models.py          VehicleModel (xe trên khung hình), AlertModel (danh sách vi phạm)
icon_provider.py   vẽ icon Lucide (SVG) -> image://icons/<tên>/<màu hex>
qml/main.qml       cửa sổ chính, lưới 12 cột giống `grid-cols-12 gap-6`
qml/TrafficOps/    Theme (singleton màu), HeaderBar, VideoPanel, BoundingBox,
                   TelemetryPanel, KpiCard, TrafficChart (Canvas), AlertPanel, AlertCard,
                   DarkComboBox, IconButton, AppIcon, CornerMask
```

## Đối chiếu React -> Qt

| React | Qt |
|---|---|
| `useState` + `setInterval` | thuộc tính / model của `TrafficBackend` + `QTimer` |
| `mockVehicles` + `VideoStreamPanel` | `VehicleModel` + `Repeater` trong `VideoPanel.qml` |
| `BoundingBox` (transition 0.5s) | `BoundingBox.qml` với `Behavior` + đường cong ease-in-out |
| `recharts` LineChart 2 trục | `TrafficChart.qml` (Canvas, đường cong monotone, tooltip khi rê chuột) |
| `initialAlerts` (tĩnh) | `AlertModel`: cảnh báo Speeding mới sinh ra khi xe vượt 85 km/h |
| `lucide-react` | `IconProvider` (Python) + `AppIcon.qml` |
| Tailwind classes | `Theme.qml` (singleton) |

## Khác biệt so với bản React

- Cảnh báo là **động**: khi xe vượt 85 km/h sẽ thêm thẻ mới lên đầu danh sách
  (cooldown 20 giây cho mỗi xe, giữ tối đa 50 cảnh báo); nhãn "2m ago" tự cập nhật.
- Xe ra khỏi khung hình thì bị xoá và một xe mới (biển số, tốc độ ngẫu nhiên) vào từ phía trên.
  Bản React cho xe "quay vòng" cùng một đối tượng.
- Ô chọn "Last 20 Mins / Last Hour" hoạt động thật (bản React chỉ là `<select>` trang trí).
- Nút Settings, Maximize, View All, chuông phát tín hiệu `settingsClicked`, `maximizeClicked`,
  `viewAllClicked`, `bellClicked` để bạn nối tiếp vào logic của mình.
- Biểu đồ vẽ bằng Canvas nên không cần thêm thư viện; muốn dùng Qt Charts / Graphs thì thay
  `TrafficChart.qml` mà không ảnh hưởng phần còn lại.

## Nối dữ liệu thật

Chỉ cần sửa `backend.py`:

- `_tick_vehicles()` — thay bằng kết quả detector (YOLO...). Mỗi xe cần `x, y, w, h` (theo % khung hình),
  `speed`, `plate`.
- `_tick_telemetry()` / `_sample()` — thay bằng cảm biến hoặc truy vấn CSDL.

Ví dụ nguồn video thật: thêm `VideoOutput` (QtMultimedia) vào `VideoPanel.qml`, ngay phía trên lớp
"NO SIGNAL / SIMULATED FEED"; các BoundingBox tự nằm trên cùng.
