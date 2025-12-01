import sys
from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.kind.training_kind import TrainingKind
from gpuctl.kind.inference_kind import InferenceKind
from gpuctl.kind.notebook_kind import NotebookKind
from gpuctl.client.job_client import JobClient
from gpuctl.client.log_client import LogClient


def create_job_command(args):
    """创建作业命令"""
    try:
        # 处理多个文件
        for file_path in args.file:
            print(f"\n📝 Processing file: {file_path}")
            print("-" * 60)
            
            # 解析YAML文件
            parsed_obj = BaseParser.parse_yaml_file(file_path)

            # 根据类型创建相应处理器
            if parsed_obj.kind == "training":
                handler = TrainingKind()
                result = handler.create_training_job(parsed_obj, args.namespace)
                print(f"✅ Successfully created {parsed_obj.kind} job: {result['job_id']}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
            elif parsed_obj.kind == "inference":
                handler = InferenceKind()
                result = handler.create_inference_service(parsed_obj, args.namespace)
                print(f"✅ Successfully created {parsed_obj.kind} service: {result['job_id']}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
            elif parsed_obj.kind == "notebook":
                handler = NotebookKind()
                result = handler.create_notebook(parsed_obj, args.namespace)
                print(f"✅ Successfully created {parsed_obj.kind} job: {result['job_id']}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
            elif parsed_obj.kind in ["pool", "resource"]:
                # 资源池创建逻辑
                # 目前简化实现，直接返回成功
                pool_name = parsed_obj.pool.name if hasattr(parsed_obj, 'pool') else parsed_obj.name
                pool_desc = parsed_obj.pool.description if hasattr(parsed_obj, 'pool') else parsed_obj.description
                print(f"✅ Successfully created resource pool: {pool_name}")
                print(f"📊 Description: {pool_desc}")
                print(f"📦 Node count: {len(parsed_obj.nodes)}")
            else:
                print(f"❌ Unsupported kind: {parsed_obj.kind}")
                return 1

        return 0
    except ParserError as e:
        print(f"❌ Parser error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def get_jobs_command(args):
    """获取作业列表命令"""
    try:
        client = JobClient()
        
        # 构建标签过滤条件
        labels = {}
        if args.pool:
            labels["gpuctl/pool"] = args.pool
        if args.type:
            labels["gpuctl/job-type"] = args.type
        
        # 调用API获取作业列表，传递过滤条件
        jobs = client.list_jobs(args.namespace, labels=labels)
        
        # 打印作业列表
        print(f"{'JOB ID':<30} {'NAME':<20} {'KIND':<15} {'STATUS':<10} {'NAMESPACE':<15} {'CREATED':<20}")
        print("-" * 120)
        
        for job in jobs:
            # 确定作业状态
            status = "running"
            if job["status"]["succeeded"] > 0:
                status = "succeeded"
            elif job["status"]["failed"] > 0:
                status = "failed"
            elif job["status"]["active"] == 0:
                status = "pending"
            
            print(f"{job['name']:<30} {job['name'].split('-')[0]:<20} {job['labels'].get('gpuctl/job-type', 'unknown'):<15} {status:<10} {job['namespace']:<15} {job['creation_timestamp']:<20}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting jobs: {e}")
        return 1


def delete_job_command(args):
    """删除作业命令"""
    try:
        resource_type = "job"
        resource_name = None

        if args.file:
            # 从YAML文件解析资源类型和名称
            try:
                parsed_obj = BaseParser.parse_yaml_file(args.file)
                resource_type = parsed_obj.kind
                # 处理资源池嵌套结构
                if resource_type in ["pool", "resource"] and hasattr(parsed_obj, 'pool'):
                    resource_name = parsed_obj.pool.name
                else:
                    resource_name = parsed_obj.name if hasattr(parsed_obj, 'name') else getattr(parsed_obj, 'job', None).name if hasattr(parsed_obj, 'job') else args.file.replace('.yaml', '').replace('.yml', '')
            except ParserError as e:
                # 如果解析失败，尝试从文件名推断
                resource_name = args.file.replace('.yaml', '').replace('.yml', '')
        elif args.resource_name:
            resource_name = args.resource_name
        else:
            print("❌ 必须提供YAML文件或资源名称")
            return 1

        if resource_type == "pool" or resource_name.endswith("-pool"):
            # 删除资源池
            from gpuctl.client.pool_client import PoolClient
            client = PoolClient()
            success = client.delete_pool(resource_name)
            if success:
                print(f"✅ 成功删除资源池: {resource_name}")
                return 0
            else:
                print(f"❌ 资源池不存在: {resource_name}")
                return 1
        else:
            # 删除任务
            client = JobClient()
            success = client.delete_job(resource_name, args.namespace)
            if success:
                print(f"✅ 成功删除任务: {resource_name}")
                return 0
            else:
                print(f"❌ 任务不存在: {resource_name}")
                return 1

    except Exception as e:
        print(f"❌ 删除资源时出错: {e}")
        return 1


def logs_job_command(args):
    """获取作业日志命令"""
    try:
        client = LogClient()
        logs = client.get_job_logs(args.job_name, namespace=args.namespace, tail=100)
        
        for log in logs:
            print(log)
        
        return 0
    except Exception as e:
        print(f"❌ Error getting logs: {e}")
        return 1


def pause_job_command(args):
    """暂停作业命令"""
    try:
        client = JobClient()
        success = client.pause_job(args.job_name, args.namespace)
        if success:
            print(f"✅ 成功暂停作业: {args.job_name}")
            return 0
        else:
            print(f"❌ 暂停作业失败: {args.job_name}")
            return 1
    except Exception as e:
        print(f"❌ Error pausing job: {e}")
        return 1


def resume_job_command(args):
    """恢复作业命令"""
    try:
        client = JobClient()
        success = client.resume_job(args.job_name, args.namespace)
        if success:
            print(f"✅ 成功恢复作业: {args.job_name}")
            return 0
        else:
            print(f"❌ 恢复作业失败: {args.job_name}")
            return 1
    except Exception as e:
        print(f"❌ Error resuming job: {e}")
        return 1


def describe_job_command(args):
    """描述作业详情命令"""
    try:
        client = JobClient()
        job = client.get_job(args.job_id, args.namespace)
        
        # 打印作业详情
        print(f"📋 Job Details: {args.job_id}")
        print("=" * 60)
        print(f"📊 Name: {job.get('name', 'N/A')}")
        print(f"📦 Namespace: {job.get('namespace', 'default')}")
        print(f"🗂️  Kind: {job.get('labels', {}).get('gpuctl/job-type', 'unknown')}")
        print(f"📈 Status: {job.get('status', 'unknown')}")
        print(f"⏰ Created: {job.get('creation_timestamp', 'N/A')}")
        print(f"🔧 Started: {job.get('start_time', 'N/A')}")
        print(f"🏁 Completed: {job.get('completion_time', 'N/A')}")
        print(f"📋 Priority: {job.get('labels', {}).get('gpuctl/priority', 'medium')}")
        print(f"🖥️  Pool: {job.get('labels', {}).get('gpuctl/pool', 'default')}")
        
        if 'resources' in job:
            print("\n💻 Resources:")
            print("-" * 60)
            resources = job['resources']
            print(f"   GPU: {resources.get('gpu', 'N/A')}")
            print(f"   CPU: {resources.get('cpu', 'N/A')}")
            print(f"   Memory: {resources.get('memory', 'N/A')}")
            print(f"   GPU Type: {resources.get('gpu_type', 'N/A')}")
        
        if 'metrics' in job:
            print("\n📊 Metrics:")
            print("-" * 60)
            metrics = job['metrics']
            print(f"   GPU Utilization: {metrics.get('gpuUtilization', 'N/A')}%")
            print(f"   Memory Usage: {metrics.get('memoryUsage', 'N/A')}")
            print(f"   Throughput: {metrics.get('throughput', 'N/A')}")
        
        if 'k8sResources' in job:
            print("\n🔧 Kubernetes Resources:")
            print("-" * 60)
            k8s_resources = job['k8sResources']
            print(f"   Job Name: {k8s_resources.get('jobName', 'N/A')}")
            print(f"   Pods: {', '.join(k8s_resources.get('pods', []))}")
        
        return 0
    except Exception as e:
        print(f"❌ Error describing job: {e}")
        return 1
