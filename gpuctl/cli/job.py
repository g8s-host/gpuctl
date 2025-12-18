import sys
from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.kind.training_kind import TrainingKind
from gpuctl.kind.inference_kind import InferenceKind
from gpuctl.kind.notebook_kind import NotebookKind
from gpuctl.client.job_client import JobClient
from gpuctl.client.log_client import LogClient


# 辅助函数：处理g8s-host前缀

def remove_prefix(name):
    """从名称中移除g8s-host前缀，只显示yaml文件中的原始名称"""
    # 对于训练任务：g8s-host-training-xxx -> xxx
    if name.startswith("g8s-host-training-"):
        return name.split("g8s-host-training-")[1]
    # 对于推理任务：g8s-host-inference-xxx -> xxx
    elif name.startswith("g8s-host-inference-"):
        return name.split("g8s-host-inference-")[1]
    # 对于notebook任务：g8s-host-notebook-xxx -> xxx
    elif name.startswith("g8s-host-notebook-"):
        return name.split("g8s-host-notebook-")[1]
    # 对于compute任务：g8s-host-compute-xxx -> xxx
    elif name.startswith("g8s-host-compute-"):
        return name.split("g8s-host-compute-")[1]
    # 对于其他g8s-host-开头的名称：g8s-host-xxx -> xxx
    elif name.startswith("g8s-host-"):
        return name.split("g8s-host-")[1]
    return name

def add_prefix(name, job_type):
    """为名称添加g8s-host前缀"""
    return f"g8s-host-{job_type}-{name}"


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
            elif parsed_obj.kind == "compute":
                from gpuctl.kind.compute_kind import ComputeKind
                handler = ComputeKind()
                result = handler.create_compute_service(parsed_obj, args.namespace)
                print(f"✅ Successfully created {parsed_obj.kind} service: {result['job_id']}")
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
        
        # 计算AGE的辅助函数
        def calculate_age(created_at_str):
            from datetime import datetime, timezone
            import math
            
            if not created_at_str:
                return "N/A"
            
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)  # 使用带时区的utcnow()
            delta = now - created_at
            
            seconds = delta.total_seconds()
            
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                return f"{int(seconds/60)}m"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h"
            else:
                return f"{int(seconds/86400)}d"
        
        # 打印作业列表
        print(f"{'NAME':<45} {'KIND':<15} {'STATUS':<10} {'AGE':<10}")
        
        for job in jobs:
            # 根据k8s状态判断，返回与k8s一致的简洁状态字符串
            status_dict = job["status"]
            
            # 对于Job资源（Training任务）
            if job['labels'].get('g8s.host/job-type') == 'training':
                if status_dict['succeeded'] > 0:
                    status = "Succeeded"
                elif status_dict['failed'] > 0:
                    status = "Failed"
                elif status_dict['active'] > 0:
                    status = "Running"
                else:
                    status = "Pending"
            # 对于Deployment资源（Inference服务）
            elif job['labels'].get('g8s.host/job-type') == 'inference':
                # Deployment的状态判断：
                # - Pending: 还没有可用的副本
                # - Running: 至少有一个可用副本
                # - Failed: 所有副本都不可用
                if status_dict['active'] > 0:
                    status = "Running"
                elif status_dict['failed'] > 0:
                    # 检查是否有pod处于Pending状态
                    status = "Pending"
                else:
                    status = "Pending"
            # 对于其他类型
            else:
                if status_dict['succeeded'] > 0:
                    status = "Succeeded"
                elif status_dict['failed'] > 0:
                    status = "Failed"
                elif status_dict['active'] > 0:
                    status = "Running"
                else:
                    status = "Pending"
            
            # 计算AGE
            age = calculate_age(job['creation_timestamp'])
            
            # 移除前缀后显示
            display_name = remove_prefix(job['name'])
            print(f"{display_name:<45} {job['labels'].get('g8s.host/job-type', 'unknown'):<15} {status:<10} {age:<10}")
        
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
            success = False
            
            # 保存原始资源名称用于最终输出
            original_resource_name = resource_name
            
            # 检查资源名称是否已经是完整名称（包含前缀）
            is_full_name = False
            if resource_name.startswith("g8s-host-"):
                is_full_name = True
            
            # 获取所有作业列表，用于查询实际的作业类型
            all_jobs = client.list_jobs(args.namespace)
            found_job = None
            
            # 在所有作业中查找匹配的作业
            for job in all_jobs:
                job_name = job['name']
                # 检查是否匹配完整名称或原始名称（不带前缀）
                if job_name == resource_name or remove_prefix(job_name) == resource_name:
                    found_job = job
                    break
            
            if found_job:
                # 从找到的作业中获取实际的作业类型
                actual_job_type = found_job['labels'].get('g8s.host/job-type', 'unknown')
                actual_job_name = found_job['name']
                
                # 根据实际作业类型调用相应的删除方法
                if actual_job_type == "training":
                    # Training任务：删除Job
                    success = client.delete_job(actual_job_name, args.namespace, force)
                elif actual_job_type == "inference" or actual_job_type == "compute":
                    # Inference或Compute任务：删除Deployment和Service
                    # 生成完整资源名称
                    service_name = f"g8s-host-svc-{resource_name}"
                    # 如果是完整名称，提取基础名称
                    if is_full_name:
                        service_name = f"g8s-host-svc-{remove_prefix(actual_job_name)}"
                    # 删除Deployment
                    deployment_deleted = client.delete_deployment(actual_job_name, args.namespace, force)
                    # 删除Service
                    service_deleted = client.delete_service(service_name, args.namespace)
                    success = deployment_deleted and service_deleted
                elif actual_job_type == "notebook":
                    # Notebook任务：删除StatefulSet和Service
                    # 生成完整资源名称
                    service_name = f"g8s-host-svc-{resource_name}"
                    # 如果是完整名称，提取基础名称
                    if is_full_name:
                        service_name = f"g8s-host-svc-{remove_prefix(actual_job_name)}"
                    # 删除StatefulSet
                    statefulset_deleted = client.delete_statefulset(actual_job_name, args.namespace, force)
                    # 删除Service
                    service_deleted = client.delete_service(service_name, args.namespace)
                    success = statefulset_deleted and service_deleted
            else:
                # 尝试使用通用方式删除（先尝试Job，再尝试Deployment，最后尝试StatefulSet）
                # 先尝试直接删除（如果是完整名称）
                if is_full_name:
                    # 直接删除完整名称
                    job_deleted = client.delete_job(resource_name, args.namespace, force)
                    if job_deleted:
                        success = True
                    else:
                        deployment_deleted = client.delete_deployment(resource_name, args.namespace, force)
                        if deployment_deleted:
                            service_name = f"g8s-host-svc-{remove_prefix(resource_name)}"
                            client.delete_service(service_name, args.namespace)
                            success = True
                        else:
                            statefulset_deleted = client.delete_statefulset(resource_name, args.namespace, force)
                            if statefulset_deleted:
                                service_name = f"g8s-host-svc-{remove_prefix(resource_name)}"
                                client.delete_service(service_name, args.namespace)
                                success = True
                else:
                    # 尝试所有可能的前缀
                    job_types = ["training", "inference", "compute", "notebook"]
                    for job_type in job_types:
                        full_name = add_prefix(resource_name, job_type)
                        if job_type == "training":
                            success = client.delete_job(full_name, args.namespace, force)
                        elif job_type == "inference" or job_type == "compute":
                            deployment_deleted = client.delete_deployment(full_name, args.namespace, force)
                            service_deleted = client.delete_service(f"g8s-host-svc-{resource_name}", args.namespace)
                            success = deployment_deleted and service_deleted
                        elif job_type == "notebook":
                            statefulset_deleted = client.delete_statefulset(full_name, args.namespace, force)
                            service_deleted = client.delete_service(f"g8s-host-svc-{resource_name}", args.namespace)
                            success = statefulset_deleted and service_deleted
                        
                        if success:
                            break
            
            if success:
                if force:
                    print(f"✅ 成功强制删除任务: {original_resource_name}")
                else:
                    print(f"✅ 成功删除任务: {original_resource_name}")
                return 0
            else:
                print(f"❌ 任务不存在: {original_resource_name}")
                return 1

    except Exception as e:
        print(f"❌ 删除资源时出错: {e}")
        return 1


def logs_job_command(args):
    """获取作业日志命令"""
    try:
        client = LogClient()
        # 无需添加前缀，因为log_client.get_job_logs已经处理了前缀逻辑
        
        if args.follow:
            # 使用流式日志，持续获取
            logs = client.stream_job_logs(args.job_name, namespace=args.namespace)
            for log in logs:
                print(log)
        else:
            # 只获取一次日志
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
            # 显示时移除前缀
            display_name = remove_prefix(args.job_name)
            print(f"✅ 成功暂停作业: {display_name}")
            return 0
        else:
            display_name = remove_prefix(args.job_name)
            print(f"❌ 暂停作业失败: {display_name}")
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
            # 显示时移除前缀
            display_name = remove_prefix(args.job_name)
            print(f"✅ 成功恢复作业: {display_name}")
            return 0
        else:
            display_name = remove_prefix(args.job_name)
            print(f"❌ 恢复作业失败: {display_name}")
            return 1
    except Exception as e:
        print(f"❌ Error resuming job: {e}")
        return 1


def describe_job_command(args):
    """描述作业详情命令"""
    try:
        client = JobClient()
        job = None
        
        # 检查资源名称是否已经是完整名称（包含前缀）
        is_full_name = False
        if args.job_id.startswith("g8s-host-"):
            is_full_name = True
        
        # 尝试直接获取作业
        job = client.get_job(args.job_id, args.namespace)
        
        if not job:
            # 获取所有作业列表，用于查询实际的作业
            all_jobs = client.list_jobs(args.namespace)
            found_job = None
            
            # 在所有作业中查找匹配的作业
            for job_item in all_jobs:
                job_name = job_item['name']
                # 检查是否匹配完整名称或原始名称（不带前缀）
                if job_name == args.job_id or remove_prefix(job_name) == args.job_id:
                    found_job = job_item
                    break
            
            if found_job:
                job = found_job
            else:
                # 尝试添加不同类型的前缀再次查找
                job_types = ["training", "inference", "notebook", "compute"]
                found = False
                for job_type in job_types:
                    prefixed_job_id = add_prefix(args.job_id, job_type)
                    job = client.get_job(prefixed_job_id, args.namespace)
                    if job:
                        found = True
                        break
                
                if not found:
                    print(f"❌ 作业不存在: {args.job_id}")
                    return 1
            
        # 打印作业详情，移除前缀
        display_name = remove_prefix(job.get('name', 'N/A'))
        print(f"📋 Job Details: {display_name}")
        print(f"📊 Name: {display_name}")
        
        # 获取任务类型和状态
        job_type = job.get('labels', {}).get('g8s.host/job-type', 'unknown')
        status_dict = job.get('status', {})
        
        # 转换为与k8s一致的状态字符串
        status = "Pending"
        if status_dict.get('succeeded', 0) > 0:
            status = "Succeeded"
        elif status_dict.get('failed', 0) > 0:
            # 对于inference任务，failed状态可能是因为pending状态导致的
            if job_type == "inference":
                status = "Pending"
            else:
                status = "Failed"
        elif status_dict.get('active', 0) > 0:
            status = "Running"
        
        # 计算AGE
        from datetime import datetime, timezone
        def calculate_age(created_at_str):
            if not created_at_str:
                return "N/A"
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - created_at
            seconds = delta.total_seconds()
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                return f"{int(seconds/60)}m"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h"
            else:
                return f"{int(seconds/86400)}d"
        
        age = calculate_age(job.get('creation_timestamp'))
        
        print(f"🗂️  Kind: {job_type}")
        print(f"📈 Status: {status}")
        print(f"⏰ Age: {age}")
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
