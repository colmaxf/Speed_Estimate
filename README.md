# Speed Estimate

Prototype ước tính tốc độ phương tiện từ video bằng **YOLOv5** để phát hiện đối tượng và **DeepSORT** để theo dõi chúng qua các khung hình. Dự án cũng có chức năng đếm đối tượng qua một đường ảo và lưu video kết quả.

> Đây là dự án thử nghiệm. Kết quả tốc độ phụ thuộc mạnh vào vị trí camera, FPS, hiệu chỉnh pixel–khoảng cách thực tế và cấu hình vùng đo; không nên dùng làm thiết bị đo tốc độ đã được kiểm định.

## Tính năng

- Phát hiện đối tượng trong video, thư mục ảnh, webcam hoặc stream được YOLOv5 hỗ trợ.
- Theo dõi đối tượng và gán ID bằng DeepSORT.
- Vẽ bounding box, đường tham chiếu và số lượng đối tượng trên khung hình.
- Lưu video đã xử lý và kết quả tracking dạng văn bản MOT.
- Có thử nghiệm ước tính tốc độ trong `test_speed.py`.

## Cấu trúc chính

```text
.
├── track.py                 # Pipeline YOLOv5 + DeepSORT và đếm đối tượng
├── test_speed.py            # Biến thể thử nghiệm có tính tốc độ
├── trackableobject.py       # Trạng thái của đối tượng được theo dõi
├── lines.json               # Một số tọa độ đường/vùng thử nghiệm
├── deep_sort/               # Mã nguồn và cấu hình DeepSORT
├── yolov5/                  # Mã nguồn YOLOv5
├── videos/                  # Thư mục video đầu vào (nếu có)
├── MOT16_eval/              # Tài nguyên đánh giá MOT
├── requirements.txt         # Các dependency bổ sung của dự án
└── yolov5n.pt               # Trọng số YOLOv5 nano
```

## Yêu cầu

- Python và pip.
- PyTorch cùng torchvision tương thích với phiên bản Python và phần cứng của bạn. Hãy cài theo hướng dẫn chính thức của [PyTorch](https://pytorch.org/get-started/locally/); dùng CPU được nhưng thường chậm hơn GPU CUDA.
- Các thư viện Python trong `requirements.txt` và `yolov5/requirements.txt`.
- Video đầu vào và trọng số mô hình cần thiết.

## Cài đặt

Clone repo và vào thư mục dự án:

```bash
git clone https://github.com/colmaxf/Speed_Estimate.git
cd Speed_Estimate
```

Nếu các tệp trọng số được lưu bằng Git LFS, cài Git LFS rồi tải nội dung thực của các tệp:

```bash
git lfs install
git lfs pull
```

Tạo môi trường ảo (khuyến nghị):

```bash
python -m venv .venv
```

Kích hoạt môi trường:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Cài PyTorch/torchvision phù hợp với máy trước, sau đó cài dependency:

```bash
pip install -r yolov5/requirements.txt
pip install -r requirements.txt
```

## Chạy

Chạy tracking và lưu video đầu ra:

```bash
python track.py --source videos/real_1.mp4 --device 0 --save-vid
```

Thử nghiệm ước tính tốc độ:

```bash
python test_speed.py --source videos/car_2.mp4 --device 0 --save-vid
```

Thay đường dẫn `--source` bằng video của bạn. Dùng `--device cpu` để chạy trên CPU; với GPU, `--device 0` chọn GPU đầu tiên. Để xem các tùy chọn khác:

```bash
python track.py --help
python test_speed.py --help
```

Đầu ra được lưu trong thư mục chạy dưới `runs/track/` theo thiết lập YOLOv5. Có thể dùng `--save-txt` để lưu kết quả tracking dạng văn bản MOT. Tùy chọn hiển thị video phụ thuộc môi trường có hỗ trợ cửa sổ OpenCV hay không.

## Cách tính tốc độ trong mã nguồn

Phần thử nghiệm trong `test_speed.py` có hai cách tính khác nhau. YOLOv5 phát hiện bounding box, còn DeepSORT giữ ID của đối tượng giữa các frame để có thể so sánh vị trí của cùng một đối tượng.

### 1. Ước tính từ chuyển động giữa hai frame

Hàm `estimateSpeed(location1, location2, ppm, fs)` lấy tâm hai bounding box liên tiếp, tính độ dịch chuyển theo pixel rồi quy đổi qua hệ số `ppm` (pixel trên mét):

```text
d_pixel = khoảng cách giữa hai tâm bounding box
d_mét   = d_pixel / ppm
v_km/h  = d_mét × FPS × 3.6
```

Trong `test_speed.py`, `ppm` hiện được đặt cố định là `10`, còn `fs` là FPS của video. Giá trị trả về được gán cho biến `speed`, nhưng nhãn tốc độ hiển thị trên bounding box lại dùng `speed1`; vì vậy phép tính theo chuyển động từng frame hiện chưa phải giá trị tốc độ đang được hiển thị. Trong `track.py`, hàm này cũng được gọi với `ppm = 10`.

### 2. Ước tính theo thời gian đi qua hai vị trí

Hàm `estimateSpeed_1(time_1, time_2)` trong `test_speed.py` dùng khoảng cách cố định 35 mét và thời gian giữa hai lần ghi nhận:

```text
v_km/h = 35 × 3.6 / (time_2 - time_1)
```

Trong mã hiện tại, biểu thức thực tế viết là `35 * 3.6 / (time_1 - time_2)`. Hàm trả về giá trị này cho `speed1`, là biến được dùng làm nhãn trên bounding box.

Thời điểm đo dự định được lưu trong `TrackableObject.time_test1` và `TrackableObject.time_test2`. Tuy nhiên, điều kiện đặt `time_test2` trong `test_speed.py` hiện có thể không bao giờ đúng: nó yêu cầu tâm box vừa lớn hơn `h - 250`, vừa nhỏ hơn `h - 350`, trong khi `h - 350` nhỏ hơn `h - 250`. Vì vậy, cách tính thứ hai cần được sửa và kiểm thử trước khi tin cậy kết quả.

### Đếm đối tượng qua vùng

`count_obj(...)` trong các script dùng track ID để tránh đếm lặp một đối tượng sau khi nó vượt ngưỡng vị trí trong khung hình. Đây là chức năng đếm lưu lượng, không phải công thức tính tốc độ.

### Lưu ý về độ chính xác

- `ppm = 10` và khoảng cách 35 mét là các giá trị giả định trong mã, không phải hiệu chuẩn tự động. Cần đo/căn chỉnh theo cảnh camera thực tế.
- Công thức theo frame giả định FPS ổn định và không bù méo phối cảnh; chuyển động hướng sâu vào camera có thể làm sai lệch đáng kể.
- Cần dùng cùng một track ID, xác định đúng hai vị trí đo và đảm bảo thời gian dương trước khi tính tốc độ.
- Hãy xác minh kết quả với khoảng cách/tốc độ đã biết. Đây là ước tính thử nghiệm, không thay thế thiết bị đo đã được kiểm định.

## Lưu ý

- Mặc định của hai script có thể trỏ tới các video mẫu khác nhau. Hãy kiểm tra thư mục `videos/` hoặc truyền `--source` phù hợp.
- Nếu thiếu model, dependency hoặc có lỗi CUDA, hãy xác nhận trọng số đã được tải đầy đủ và phiên bản PyTorch/torchvision tương thích với môi trường.
- Repo chứa mã nguồn phụ thuộc YOLOv5 và DeepSORT với các tệp giấy phép riêng trong thư mục tương ứng. Hãy kiểm tra điều khoản của các thành phần đó trước khi phân phối hoặc sử dụng thương mại.

## Đóng góp

Issue và pull request được hoan nghênh. Khi báo lỗi, vui lòng nêu hệ điều hành, phiên bản Python/PyTorch, thiết bị chạy và lệnh đã dùng.
