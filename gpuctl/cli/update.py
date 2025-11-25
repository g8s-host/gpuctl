import argparse
import sys
from gpuctl.client.job_client import JobClient
from gpuctl.parser.base_parser import BaseParser, ParserError


def update_command(args):
    """处理update命令"""
    try:
        client = JobClient()

        if args.file:
            # 从YAML文件解析更新内容
            parsed_obj = BaseParser.parse_yaml_file(args.file)
            job_name = parsed_obj.spec.job.name

            if args.resource == 'scale':
                # 扩展资源
                return scale_job(client, job_name, args.namespace, parsed_obj)
            elif args.resource == 'priority':
                # 更新优先级
                return update_priority(client, job_name, args.namespace, parsed_obj)
            else:
                print(f"❌ 不支持的更新操作: {args.resource}")
                return 1
        else:
            print("❌ 必须提供YAML文件")
            return 1

    except ParserError as e:
        print(f"❌ YAML解析错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 更新任务时出错: {e}")
        return 1


def scale_job(client, job_name, namespace, parsed_obj):
    """扩展任务资源"""
    try:
        # 获取当前Job
        job_info = client.get_job(job_name, namespace)
        if not job_info:
            print(f"❌ 任务不存在: {job_name}")
            return 1

        # 更新资源规格
        new_resources = parsed_obj.spec.resources
        success = client.update_job_resources(job_name, namespace, new_resources)

        if success:
            print(f"✅ 成功扩展任务资源: {job_name}")
            print(f"📊 新资源规格:")
            print(f"   GPU: {new_resources.accelerator_count}")
            print(f"   CPU: {new_resources.cpu}")
            print(f"   内存: {new_resources.memory}")
            return 0
        else:
            print(f"❌ 扩展任务资源失败: {job_name}")
            return 1

    except Exception as e:
        print(f"❌ 扩展资源时出错: {e}")
        return 1


def update_priority(client, job_name, namespace, parsed_obj):
    """更新任务优先级"""
    try:
        new_priority = parsed_obj.spec.job.priority
        success = client.update_job_priority(job_name, namespace, new_priority)

        if success:
            print(f"✅ 成功更新任务优先级: {job_name} -> {new_priority}")
            return 0
        else:
            print(f"❌ 更新任务优先级失败: {job_name}")
            return 1

    except Exception as e:
        print(f"❌ 更新优先级时出错: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Update job resources or priority')
    parser.add_argument('resource', choices=['scale', 'priority'], help='Resource to update')
    parser.add_argument('-f', '--file', required=True, help='YAML file with updated configuration')
    parser.add_argument('-n', '--namespace', default='default', help='Kubernetes namespace')

    args = parser.parse_args()
    sys.exit(update_command(args))


if __name__ == '__main__':
    main()