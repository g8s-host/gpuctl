import argparse
import sys
from gpuctl.client.job_client import JobClient


def delete_command(args):
    """处理delete命令"""
    try:
        client = JobClient()

        if args.file:
            # 从YAML文件解析任务名称
            # 这里简化实现，实际需要解析YAML获取任务名称
            job_name = args.file.replace('.yaml', '').replace('.yml', '')
        elif args.job_name:
            job_name = args.job_name
        else:
            print("❌ 必须提供YAML文件或任务名称")
            return 1

        success = client.delete_job(job_name, args.namespace)

        if success:
            print(f"✅ 成功删除任务: {job_name}")
            return 0
        else:
            print(f"❌ 任务不存在: {job_name}")
            return 1

    except Exception as e:
        print(f"❌ 删除任务时出错: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Delete GPU job')
    parser.add_argument('-f', '--file', help='YAML file path')
    parser.add_argument('job_name', nargs='?', help='Job name')
    parser.add_argument('-n', '--namespace', default='default', help='Kubernetes namespace')

    args = parser.parse_args()
    sys.exit(delete_command(args))


if __name__ == '__main__':
    main()