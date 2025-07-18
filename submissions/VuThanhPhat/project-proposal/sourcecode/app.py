import boto3
import os
from PIL import Image
import io

# Khởi tạo S3 client để tương tác với dịch vụ S3
s3_client = boto3.client('s3')

# Lấy tên bucket đích từ biến môi trường được định nghĩa trong template.yaml
# Nếu không có, sử dụng một giá trị mặc định để tránh lỗi
DEST_BUCKET = os.environ.get('DEST_BUCKET', 'default-dest-bucket-name')
# Định nghĩa kích thước cố định cho ảnh thumbnail
THUMB_SIZE = 128, 128

def lambda_handler(event, context):
    """
    Hàm chính của Lambda, được kích hoạt bởi sự kiện S3.
    Hàm này sẽ đọc ảnh từ bucket nguồn, tạo thumbnail và lưu vào bucket đích.
    """
    print("Received event:", event)

    # Lặp qua tất cả các bản ghi trong sự kiện (thường chỉ có 1 khi tải lên 1 file)
    for record in event['Records']:
        # Trích xuất thông tin cần thiết từ sự kiện
        source_bucket = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']

        print(f"Processing object {object_key} from bucket {source_bucket}.")

        try:
            # Tải đối tượng ảnh từ S3 vào bộ nhớ của Lambda
            response = s3_client.get_object(Bucket=source_bucket, Key=object_key)
            image_content = response['Body'].read()

            # Sử dụng thư viện Pillow để mở ảnh từ dữ liệu bytes trong bộ nhớ
            with Image.open(io.BytesIO(image_content)) as image:
                # Tạo thumbnail với kích thước đã định nghĩa, giữ nguyên tỷ lệ
                image.thumbnail(THUMB_SIZE)

                # Chuẩn bị một buffer trong bộ nhớ để lưu ảnh thumbnail đã xử lý
                buffer = io.BytesIO()
                # Lưu ảnh dưới định dạng JPEG. Có thể thay đổi thành PNG nếu cần.
                image.save(buffer, format="JPEG")
                # Di chuyển con trỏ về đầu buffer để chuẩn bị cho việc đọc
                buffer.seek(0)

                # Tạo tên file mới cho thumbnail, ví dụ: "thumb-my-image.jpg"
                dest_key = f"thumb-{os.path.basename(object_key)}"

                print(f"Uploading thumbnail {dest_key} to bucket {DEST_BUCKET}.")

                # Tải thumbnail lên bucket đích
                s3_client.put_object(
                    Bucket=DEST_BUCKET,
                    Key=dest_key,
                    Body=buffer,
                    ContentType='image/jpeg'
                )

                print(f"Successfully processed and uploaded {dest_key}.")

        except Exception as e:
            print(f"Error processing object {object_key} from bucket {source_bucket}: {str(e)}")
            # Ném lỗi để AWS Lambda biết rằng việc thực thi đã thất bại
            # và có thể tự động thử lại hoặc ghi nhận lỗi trong CloudWatch
            raise e

    return {
        'statusCode': 200,
        'body': 'Image processing completed successfully!'
    }