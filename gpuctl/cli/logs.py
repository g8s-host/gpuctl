import argparse
import sys
from gpuctl.client.log_client import LogClient


def logs_command(args):
    """处理logs命令"""
    try:
        client = LogClient()

        if args.follow:
            # 流式日志
            print(f"开始流式日志输出（任务: {args.job_name}，命名空间: {args.namespace}）")
            print("-" * 80)

            try:
                for line in client.stream_job_logs(args.job_name, args.namespace):
                    if line:
                        print(line)
            except KeyboardInterrupt:
                print("\n停止日志流")
                return 0

        else:
            # 获取历史日志
            logs = client.get_job_logs(
                args.job_name,
                args.namespace,
                tail=args.tail,
                pod_name=args.pod
            )

            if not logs:
                print("未找到日志")
                return 0

            print(f"任务 {args.job_name} 的日志（最近 {args.tail} 行）:")
            print("-" * 80)
            for log in logs:
                print(log)

        return 0

    except Exception as e:
        print(f"❌ 获取日志时出错: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Get job logs')
    parser.add_argument('job_name', help='Job name')
    parser.add_argument('-n', '--namespace', default='default', help='Kubernetes namespace')
    parser.add_argument('-f', '--follow', action='store_true', help='Follow log output')
    parser.add_argument('--tail', type=int, default=100, help='Number of lines to show from the end')
    parser.add_argument('--pod', help='Specific pod name (for multi-pod jobs)')

    args = parser.parse_args()
    sys.exit(logs_command(args))


if __name__ == '__main__':
    main()