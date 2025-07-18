# lambda_function.py

import boto3
import os
from io import BytesIO
from PIL import Image

# Khởi tạo client S3 một lần bên ngoài handler để tái sử dụng
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Hàm chính được Lambda thực thi khi có sự kiện S3 trigger.
    """
    # Lấy thông tin về bucket và key (tên file) từ sự kiện S3
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']

    # Lấy tên bucket output từ biến môi trường, với một giá trị mặc định
    # Bạn nên vào phần Configuration -> Environment variables của Lambda để thiết lập biến này
    # Key: OUTPUT_BUCKET, Value: tên-bucket-output-của-bạn
    output_bucket = os.environ.get('OUTPUT_BUCKET', 'yourname-workshop-output-images')
    
    print(f"Sự kiện được kích hoạt cho file: {object_key} trong bucket: {bucket_name}")

    try:
        # 1. Tải file ảnh từ S3 bucket gốc vào bộ nhớ (in-memory)
        # Sử dụng BytesIO để xử lý file như một file trong bộ nhớ, không cần lưu xuống đĩa
        file_byte_string = s3_client.get_object(Bucket=bucket_name, Key=object_key)['Body'].read()
        image = Image.open(BytesIO(file_byte_string))

        # 2. Thay đổi kích thước ảnh để tạo thumbnail
        thumbnail_size = (200, 200)
        image.thumbnail(thumbnail_size)

        # 3. Lưu ảnh thumbnail vào một buffer trong bộ nhớ
        # Định dạng ảnh có thể là JPEG hoặc PNG tùy vào file gốc
        buffer = BytesIO()
        file_extension = os.path.splitext(object_key)[1].lower()
        
        if file_extension in ['.jpeg', '.jpg']:
            image_format = 'JPEG'
        elif file_extension == '.png':
            image_format = 'PNG'
        else:
            print(f"Định dạng file không được hỗ trợ: {file_extension}")
            return {'statusCode': 400, 'body': 'Unsupported file format'}

        image.save(buffer, format=image_format)
        buffer.seek(0) # Đưa con trỏ về đầu buffer để sẵn sàng cho việc đọc

        # 4. Tải ảnh thumbnail đã xử lý lên S3 bucket đích
        thumbnail_key = f"thumb-{object_key}"
        s3_client.put_object(
            Bucket=output_bucket,
            Key=thumbnail_key,
            Body=buffer,
            ContentType=f'image/{image_format.lower()}'
        )

        print(f"Đã tạo thumbnail thành công: {thumbnail_key} trong bucket: {output_bucket}")
        
        return {
            'statusCode': 200,
            'body': f'Successfully created thumbnail for {object_key}'
        }

    except Exception as e:
        print(f"Lỗi xử lý ảnh: {e}")
        # Trả về lỗi để có thể theo dõi trên CloudWatch
        raise e
