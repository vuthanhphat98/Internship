# lambda_function.py

# 1. Import các thư viện cần thiết
import boto3  # AWS SDK cho Python, để tương tác với các dịch vụ AWS
import os  # Để tương tác với hệ điều hành, ở đây dùng để đọc biến môi trường
from io import BytesIO  # Để xử lý dữ liệu nhị phân (ảnh) trong bộ nhớ
from PIL import Image  # Thư viện Pillow để xử lý ảnh

# 2. Khởi tạo client S3
# Đây là một best practice để cải thiện hiệu năng.
# Client được khởi tạo một lần khi môi trường Lambda được tạo ra (cold start)
# và được tái sử dụng cho các lần gọi tiếp theo (warm start),
# tránh việc tạo kết nối mới mỗi lần hàm được gọi.
s3_client = boto3.client('s3')

# 3. Định nghĩa hàm handler chính
# Đây là hàm mà dịch vụ Lambda sẽ gọi khi có sự kiện kích hoạt.
# Nó nhận hai tham số: `event` chứa dữ liệu sự kiện (từ S3) và `context` chứa thông tin về môi trường thực thi.
def lambda_handler(event, context):
    """
    Hàm chính được Lambda thực thi khi có sự kiện S3 trigger.
    """
    
    # 4. Trích xuất thông tin từ sự kiện S3
    # Cấu trúc của `event` được S3 định nghĩa sẵn. Chúng ta truy cập vào các key để lấy thông tin cần thiết.
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']

    # Lấy tên bucket output từ biến môi trường để code linh hoạt hơn.
    # Nếu không có biến môi trường, dùng một giá trị mặc định.
    # Bạn nên vào phần Configuration -> Environment variables của Lambda để thiết lập biến này.
    output_bucket = os.environ.get('OUTPUT_BUCKET', 'yourname-workshop-output-images')
    
    print(f"Sự kiện được kích hoạt cho file: {object_key} trong bucket: {bucket_name}")

    # 5. Kiểm tra để tránh vòng lặp vô hạn
    # Nếu tên file đã chứa "thumb-", có nghĩa nó là một thumbnail đã được xử lý.
    # Chúng ta sẽ bỏ qua để tránh việc xử lý lại chính nó.
    if "thumb-" in object_key:
        print("Đây đã là thumbnail, bỏ qua xử lý.")
        return {'statusCode': 200, 'body': 'Already a thumbnail'}

    # 6. Sử dụng khối try...except để bắt lỗi
    # Bất kỳ lỗi nào xảy ra trong quá trình xử lý sẽ được bắt lại, ghi log và ném ra ngoài.
    try:
        # 7. Tải file ảnh từ S3 vào bộ nhớ
        # `get_object` trả về một đối tượng, nội dung file nằm trong key 'Body'.
        # `.read()` sẽ đọc toàn bộ nội dung nhị phân của file.
        file_byte_string = s3_client.get_object(Bucket=bucket_name, Key=object_key)['Body'].read()
        
        # 8. Xử lý ảnh với Pillow
        # Mở ảnh từ chuỗi bytes trong bộ nhớ.
        image = Image.open(BytesIO(file_byte_string))
        
        # Định nghĩa kích thước thumbnail.
        thumbnail_size = (200, 200)
        
        # `thumbnail()` sẽ thay đổi kích thước ảnh mà vẫn giữ nguyên tỷ lệ.
        image.thumbnail(thumbnail_size)

        # 9. Lưu ảnh thumbnail vào một buffer trong bộ nhớ
        # BytesIO tạo ra một đối tượng hoạt động như một file trong RAM.
        buffer = BytesIO()
        
        # Xác định định dạng file để lưu cho đúng.
        file_extension = os.path.splitext(object_key)[1].lower()
        if file_extension in ['.jpeg', '.jpg']:
            image_format = 'JPEG'
        elif file_extension == '.png':
            image_format = 'PNG'
        else:
            # Nếu định dạng không hỗ trợ, ghi log và thoát một cách nhẹ nhàng.
            print(f"Định dạng file không được hỗ trợ: {file_extension}")
            return {'statusCode': 400, 'body': 'Unsupported file format'}

        # Lưu ảnh đã xử lý vào buffer.
        image.save(buffer, format=image_format)
        
        # Di chuyển con trỏ về đầu buffer để sẵn sàng cho việc đọc và tải lên.
        buffer.seek(0)

        # 10. Tải ảnh thumbnail lên S3 bucket đích
        # Tạo một tên file mới cho thumbnail.
        thumbnail_key = f"thumb-{object_key}"
        
        # Sử dụng `put_object` để tải nội dung từ buffer lên S3.
        # `ContentType` giúp trình duyệt hiểu và hiển thị file ảnh đúng cách.
        s3_client.put_object(
            Bucket=output_bucket,
            Key=thumbnail_key,
            Body=buffer,
            ContentType=f'image/{image_format.lower()}'
        )

        print(f"Đã tạo thumbnail thành công: {thumbnail_key} trong bucket: {output_bucket}")
        
        # 11. Trả về kết quả thành công
        return {
            'statusCode': 200,
            'body': f'Successfully created thumbnail for {object_key}'
        }

    except Exception as e:
        # 12. Xử lý lỗi
        print(f"Lỗi xử lý ảnh: {e}")
        # Ném lỗi ra ngoài để Lambda có thể thử lại hoặc gửi sự kiện vào Dead-Letter Queue.
        raise e
