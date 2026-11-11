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

## Độ chính xác tốc độ

Phần ước tính trong `test_speed.py` hiện là logic thử nghiệm, không phải hiệu chuẩn tổng quát cho mọi camera. Mã có giá trị `ppm` (pixel trên mét) cố định và dùng FPS của video; chất lượng ước tính vì vậy không thể đảm bảo khi đổi camera, độ phân giải, góc nhìn hoặc vùng đo. Cần hiệu chuẩn theo cảnh thực tế và kiểm tra lại công thức/thời gian đo trước khi sử dụng kết quả.

## Lưu ý

- Mặc định của hai script có thể trỏ tới các video mẫu khác nhau. Hãy kiểm tra thư mục `videos/` hoặc truyền `--source` phù hợp.
- Nếu thiếu model, dependency hoặc có lỗi CUDA, hãy xác nhận trọng số đã được tải đầy đủ và phiên bản PyTorch/torchvision tương thích với môi trường.
- Repo chứa mã nguồn phụ thuộc YOLOv5 và DeepSORT với các tệp giấy phép riêng trong thư mục tương ứng. Hãy kiểm tra điều khoản của các thành phần đó trước khi phân phối hoặc sử dụng thương mại.

## Đóng góp

Issue và pull request được hoan nghênh. Khi báo lỗi, vui lòng nêu hệ điều hành, phiên bản Python/PyTorch, thiết bị chạy và lệnh đã dùng.
