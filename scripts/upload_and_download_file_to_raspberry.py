import os
import paramiko
import stat


# 配置树莓派信息
PI_HOST = "192.168.1.13"   # 树莓派IP
PI_PORT = 22                # SSH端口，默认22
PI_USER = "raspberry"              # 用户名
PI_PASS = "raspberry"       # 密码

def sftp_connect():
    """建立 SFTP 连接"""
    transport = paramiko.Transport((PI_HOST, PI_PORT))
    transport.connect(username=PI_USER, password=PI_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return sftp, transport

def upload_file(local_path, remote_path):
    """上传单个文件"""
    sftp, transport = sftp_connect()
    sftp.put(local_path, remote_path)
    print(f"上传成功: {local_path} -> {remote_path}")
    sftp.close()
    transport.close()

def download_file(remote_path, local_path):
    """下载单个文件"""
    sftp, transport = sftp_connect()
    sftp.get(remote_path, local_path)
    print(f"下载成功: {remote_path} -> {local_path}")
    sftp.close()
    transport.close()

def upload_folder(local_folder, remote_folder):
    """递归上传整个文件夹"""
    sftp, transport = sftp_connect()
    try:
        sftp.mkdir(remote_folder)
    except IOError:
        pass  # 文件夹已存在则跳过

    for root, dirs, files in os.walk(local_folder):
        remote_path = remote_folder + root.replace(local_folder, "").replace("\\", "/")
        try:
            sftp.mkdir(remote_path)
        except IOError:
            pass
        for file in files:
            local_file = os.path.join(root, file)
            remote_file = remote_path + "/" + file
            sftp.put(local_file, remote_file)
            print(f"上传: {local_file} -> {remote_file}")

    sftp.close()
    transport.close()
    print("文件夹上传完成")

def download_folder(remote_dir, local_dir):
    sftp, transport = sftp_connect()

    def _download_dir(remote_dir, local_dir):
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        for item in sftp.listdir_attr(remote_dir):
            # ✅ 忽略 venv
            if item.filename == "venv":
                print(f"⏭️ 跳过目录: {remote_dir}/{item.filename}")
                continue

            remote_path = remote_dir + "/" + item.filename
            local_path = os.path.join(local_dir, item.filename)

            mode = item.st_mode

            if stat.S_ISDIR(mode):
                _download_dir(remote_path, local_path)

            elif stat.S_ISREG(mode):
                try:
                    sftp.get(remote_path, local_path)
                    print(f"下载: {remote_path} -> {local_path}")
                except Exception as e:
                    print(f"❌ 下载失败: {remote_path}, 错误: {e}")

            else:
                print(f"⚠️ 跳过特殊文件: {remote_path}")

    try:
        _download_dir(remote_dir, local_dir)
        print("文件夹下载完成")
    finally:
        sftp.close()
        transport.close()

if __name__ == "__main__":
    # 示例：上传文件
    #upload_file("openclaw.json", "/home/raspberry/Desktop/openclaw.json")

    # 示例：下载文件
    download_file("/home/raspberry/.openclaw/openclaw.json", "openclaw.json")

    # 示例：上传文件夹
    #upload_folder(r"C:\Users\Administrator\Desktop\agent\market-trader", "/home/raspberry/Desktop/market-trader")

    # 示例：下载文件夹
    # download_folder(r"/home/raspberry/.openclaw/workspace-market-trader", r"D:\Project\agent\market-trader")
