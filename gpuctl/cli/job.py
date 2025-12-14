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
            elif parsed_obj.kind == "pool" or parsed_obj.kind == "resource":
                # 资源池创建逻辑
                from gpuctl.client.pool_client import PoolClient
                client = PoolClient()
                
                # 构建资源池配置
                pool_config = {
                    "name": parsed_obj.metadata.name,
                    "description": parsed_obj.metadata.description,
                    "nodes": list(parsed_obj.nodes.keys())
                }
                
                # 创建资源池
                result = client.create_pool(pool_config)
                print(f"✅ Successfully created resource pool: {result['name']}")
                print(f"📊 Description: {parsed_obj.metadata.description}")
                print(f"📦 Node count: {len(parsed_obj.nodes)}")
                print(f"📋 Status: {result['status']}")
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
            labels["g8s.host/pool"] = args.pool
        if args.type:
            labels["g8s.host/job-type"] = args.type
        
        # 调用API获取作业列表，传递过滤条件
        jobs = client.list_jobs(args.namespace, labels=labels)
        
        # 打印作业列表
        print(f"{'JOB ID':<30} {'NAME':<20} {'KIND':<15} {'STATUS':<10} {'NAMESPACE':<15} {'CREATED':<20}")
        
        for job in jobs:
            # 确定作业状态
            status = "running"
            if job["status"]["succeeded"] > 0:
                status = "succeeded"
            elif job["status"]["failed"] > 0:
                status = "failed"
            elif job["status"]["active"] == 0:
                status = "pending"
            
            print(f"{job['name']:<30} {job['name'].split('-')[0]:<20} {job['labels'].get('g8s.host/job-type', 'unknown'):<15} {status:<10} {job['namespace']:<15} {job['creation_timestamp']:<20}")
        
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
                if resource_type in ["pool", "resource"]:
                    # 资源池处理
                    if hasattr(parsed_obj, 'metadata') and hasattr(parsed_obj.metadata, 'name'):
                        resource_name = parsed_obj.metadata.name
                    elif hasattr(parsed_obj, 'pool') and hasattr(parsed_obj.pool, 'name'):
                        resource_name = parsed_obj.pool.name
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                elif resource_type in ["training", "inference", "notebook"]:
                    # 任务处理
                    if hasattr(parsed_obj, 'job') and hasattr(parsed_obj.job, 'name'):
                        resource_name = parsed_obj.job.name
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                else:
                    # 其他类型，从文件名推断
                    resource_name = args.file.replace('.yaml', '').replace('.yml', '')
            except ParserError as e:
                # 如果解析失败，尝试从文件名推断
                resource_name = args.file.replace('.yaml', '').replace('.yml', '')
        elif args.resource_name:
            resource_name = args.resource_name
        else:
            print("❌ 必须提供YAML文件或资源名称")
            return 1

        if resource_type == "pool" or resource_type == "resource" or resource_name.endswith("-pool"):
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
            # 检查是否有force属性
            force = getattr(args, 'force', False)
            success = True
            
            # 根据任务类型调用相应的删除方法
            if resource_type == "training":
                # Training任务：删除Job
                success = client.delete_job(resource_name, args.namespace, force)
            elif resource_type == "inference":
                # Inference任务：删除Deployment和Service
                # 生成完整资源名称
                deployment_name = f"inference-{resource_name}"
                service_name = f"svc-{resource_name}"
                # 删除Deployment
                deployment_deleted = client.delete_deployment(deployment_name, args.namespace, force)
                # 删除Service
                service_deleted = client.delete_service(service_name, args.namespace)
                success = deployment_deleted and service_deleted
            elif resource_type == "notebook":
                # Notebook任务：删除StatefulSet和Service
                # 生成完整资源名称
                statefulset_name = f"notebook-{resource_name}"
                service_name = f"svc-{resource_name}"
                # 删除StatefulSet
                statefulset_deleted = client.delete_statefulset(statefulset_name, args.namespace, force)
                # 删除Service
                service_deleted = client.delete_service(service_name, args.namespace)
                success = statefulset_deleted and service_deleted
            else:
                # 尝试使用通用方式删除（先尝试Job，再尝试Deployment，最后尝试StatefulSet）
                job_deleted = client.delete_job(resource_name, args.namespace, force)
                if not job_deleted:
                    deployment_deleted = client.delete_deployment(f"inference-{resource_name}", args.namespace, force)
                    if deployment_deleted:
                        client.delete_service(f"svc-{resource_name}", args.namespace)
                        success = True
                    else:
                        statefulset_deleted = client.delete_statefulset(f"notebook-{resource_name}", args.namespace, force)
                        if statefulset_deleted:
                            client.delete_service(f"svc-{resource_name}", args.namespace)
                            success = True
                        else:
                            success = False
                else:
                    success = True
            
            if success:
                if force:
                    print(f"✅ 成功强制删除任务: {resource_name}")
                else:
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
        print(f"📊 Name: {job.get('name', 'N/A')}")
        print(f"📦 Namespace: {job.get('namespace', 'default')}")
        print(f"🗂️  Kind: {job.get('labels', {}).get('g8s.host/job-type', 'unknown')}")
        print(f"📈 Status: {job.get('status', 'unknown')}")
        print(f"⏰ Created: {job.get('creation_timestamp', 'N/A')}")
        print(f"🔧 Started: {job.get('start_time', 'N/A')}")
        print(f"🏁 Completed: {job.get('completion_time', 'N/A')}")
        print(f"📋 Priority: {job.get('labels', {}).get('g8s.host/priority', 'medium')}")
        print(f"🖥️  Pool: {job.get('labels', {}).get('g8s.host/pool', 'default')}")
        
        if 'resources' in job:
            print("\n💻 Resources:")
            resources = job['resources']
            print(f"   GPU: {resources.get('gpu', 'N/A')}")
            print(f"   CPU: {resources.get('cpu', 'N/A')}")
            print(f"   Memory: {resources.get('memory', 'N/A')}")
            print(f"   GPU Type: {resources.get('gpu_type', 'N/A')}")
        
        if 'metrics' in job:
            print("\n📊 Metrics:")
            metrics = job['metrics']
            print(f"   GPU Utilization: {metrics.get('gpuUtilization', 'N/A')}%")
            print(f"   Memory Usage: {metrics.get('memoryUsage', 'N/A')}")
            print(f"   Throughput: {metrics.get('throughput', 'N/A')}")
        
        if 'k8sResources' in job:
            print("\n🔧 Kubernetes Resources:")
            k8s_resources = job['k8sResources']
            print(f"   Job Name: {k8s_resources.get('jobName', 'N/A')}")
            print(f"   Pods: {', '.join(k8s_resources.get('pods', []))}")
        
        return 0
    except Exception as e:
        print(f"❌ Error describing job: {e}")
        return 1
