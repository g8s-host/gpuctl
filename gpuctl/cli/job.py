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
                # 移除前缀后显示job_id
                display_job_id = remove_prefix(result['job_id'])
                print(f"✅ Successfully created {parsed_obj.kind} job: {display_job_id}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
            elif parsed_obj.kind == "inference":
                handler = InferenceKind()
                result = handler.create_inference_service(parsed_obj, args.namespace)
                # 移除前缀后显示job_id
                display_job_id = remove_prefix(result['job_id'])
                print(f"✅ Successfully created {parsed_obj.kind} service: {display_job_id}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
                
                # 显示Access Methods
                print("\n🌐 Access Methods:")
                
                try:
                    import subprocess
                    import json
                    
                    # 获取Service信息
                    service_base_name = result['name']
                    service_cmd = f"kubectl get svc g8s-host-svc-{service_base_name} -n g8s-host -o json"
                    service_output = subprocess.check_output(service_cmd, shell=True, text=True)
                    service_data = json.loads(service_output)
                    
                    # 获取Node IP
                    node_cmd = f"kubectl get nodes -o json"
                    node_output = subprocess.check_output(node_cmd, shell=True, text=True)
                    node_data = json.loads(node_output)
                    node_ip = node_data['items'][0]['status']['addresses'][0]['address'] if node_data['items'] else 'N/A'
                    
                    # 获取Service的端口信息
                    node_port = service_data['spec']['ports'][0]['nodePort'] if service_data['spec']['ports'] and 'nodePort' in service_data['spec']['ports'][0] else 'N/A'
                    service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                    target_port = service_data['spec']['ports'][0]['targetPort'] if service_data['spec']['ports'] else 'N/A'
                    
                    # 方式1: 通过Pod IP访问
                    print(f"   1. Pod IP Access:")
                    print(f"      - Pod is initializing, IP will be available once running")
                    print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                    
                    # 方式2: 通过NodePort访问
                    print(f"   2. NodePort Access:")
                    print(f"      - Node IP: {node_ip}")
                    print(f"      - NodePort: {node_port}")
                    if node_port != 'N/A':
                        print(f"      - Access: curl http://{node_ip}:{node_port}")
                    else:
                        print(f"      - NodePort not available")
                except Exception as e:
                    print(f"      - Access methods information not available yet")
            elif parsed_obj.kind == "notebook":
                handler = NotebookKind()
                result = handler.create_notebook(parsed_obj, args.namespace)
                # 移除前缀后显示job_id
                display_job_id = remove_prefix(result['job_id'])
                print(f"✅ Successfully created {parsed_obj.kind} job: {display_job_id}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
                
                # 显示Access Methods
                print("\n🌐 Access Methods:")
                
                try:
                    import subprocess
                    import json
                    
                    # 获取Service信息
                    service_base_name = result['name']
                    service_cmd = f"kubectl get svc g8s-host-svc-{service_base_name} -n g8s-host -o json"
                    service_output = subprocess.check_output(service_cmd, shell=True, text=True)
                    service_data = json.loads(service_output)
                    
                    # 获取Node IP
                    node_cmd = f"kubectl get nodes -o json"
                    node_output = subprocess.check_output(node_cmd, shell=True, text=True)
                    node_data = json.loads(node_output)
                    node_ip = node_data['items'][0]['status']['addresses'][0]['address'] if node_data['items'] else 'N/A'
                    
                    # 获取Service的端口信息
                    node_port = service_data['spec']['ports'][0]['nodePort'] if service_data['spec']['ports'] and 'nodePort' in service_data['spec']['ports'][0] else 'N/A'
                    service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                    target_port = service_data['spec']['ports'][0]['targetPort'] if service_data['spec']['ports'] else 'N/A'
                    
                    # 方式1: 通过Pod IP访问
                    print(f"   1. Pod IP Access:")
                    print(f"      - Pod is initializing, IP will be available once running")
                    print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                    
                    # 方式2: 通过NodePort访问
                    print(f"   2. NodePort Access:")
                    print(f"      - Node IP: {node_ip}")
                    print(f"      - NodePort: {node_port}")
                    if node_port != 'N/A':
                        print(f"      - Access: curl http://{node_ip}:{node_port}")
                    else:
                        print(f"      - NodePort not available")
                except Exception as e:
                    print(f"      - Access methods information not available yet")
            elif parsed_obj.kind == "compute":
                from gpuctl.kind.compute_kind import ComputeKind
                handler = ComputeKind()
                result = handler.create_compute_service(parsed_obj, args.namespace)
                # 移除前缀后显示job_id
                display_job_id = remove_prefix(result['job_id'])
                print(f"✅ Successfully created {parsed_obj.kind} service: {display_job_id}")
                print(f"📊 Name: {result['name']}")
                print(f"📦 Namespace: {result['namespace']}")
                if 'resources' in result:
                    print(f"🖥️  Resources: {result['resources']}")
                
                # 显示Access Methods
                print("\n🌐 Access Methods:")
                
                try:
                    import subprocess
                    import json
                    
                    # 获取Service信息
                    service_base_name = result['name']
                    service_cmd = f"kubectl get svc g8s-host-svc-{service_base_name} -n g8s-host -o json"
                    service_output = subprocess.check_output(service_cmd, shell=True, text=True)
                    service_data = json.loads(service_output)
                    
                    # 获取Node IP
                    node_cmd = f"kubectl get nodes -o json"
                    node_output = subprocess.check_output(node_cmd, shell=True, text=True)
                    node_data = json.loads(node_output)
                    node_ip = node_data['items'][0]['status']['addresses'][0]['address'] if node_data['items'] else 'N/A'
                    
                    # 获取Service的端口信息
                    node_port = service_data['spec']['ports'][0]['nodePort'] if service_data['spec']['ports'] and 'nodePort' in service_data['spec']['ports'][0] else 'N/A'
                    service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                    target_port = service_data['spec']['ports'][0]['targetPort'] if service_data['spec']['ports'] else 'N/A'
                    
                    # 方式1: 通过Pod IP访问
                    print(f"   1. Pod IP Access:")
                    print(f"      - Pod is initializing, IP will be available once running")
                    print(f"      - Expected Port: {target_port if target_port != 'N/A' else service_port}")
                    
                    # 方式2: 通过NodePort访问
                    print(f"   2. NodePort Access:")
                    print(f"      - Node IP: {node_ip}")
                    print(f"      - NodePort: {node_port}")
                    if node_port != 'N/A':
                        print(f"      - Access: curl http://{node_ip}:{node_port}")
                    else:
                        print(f"      - NodePort not available")
                except Exception as e:
                    print(f"      - Access methods information not available yet")
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
        # 默认显示Pod实例，将include_pods设置为True
        jobs = client.list_jobs(args.namespace, labels=labels, include_pods=True)
        
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
        print(f"{'JOB ID':<55} {'NAME':<20} {'KIND':<15} {'STATUS':<10} {'AGE':<10}")
        
        for job in jobs:
            # 计算AGE
            age = calculate_age(job.get('creation_timestamp'))
            
            # 获取作业类型
            job_type = job['labels'].get('g8s.host/job-type', 'unknown')
            
            # 直接使用job中的状态信息，这些信息已经在_pod_to_dict中根据Pod实际状态设置
            status_dict = job.get("status", {})
            
            # 根据active、succeeded、failed字段直接判断状态，与k8s保持一致
            if status_dict.get('succeeded', 0) > 0:
                status = "Succeeded"
            elif status_dict.get('failed', 0) > 0:
                status = "Failed"
            elif status_dict.get('active', 0) > 0:
                status = "Running"
            else:
                status = "Pending"
            
            # 显示名称时移除前缀，只显示yaml文件中的原始名称，方便用户对应
            yaml_name = remove_prefix(job['name'])
            
            # 获取作业类型
            job_type = job['labels'].get('g8s.host/job-type', 'unknown')
            
            # 从yaml_name中提取基础名称
            parts = yaml_name.split('-')
            base_name = yaml_name
            
            if job_type == 'notebook':
                # StatefulSet Pod格式：base-name-index (如new-test-notebook-job-0)
                if len(parts) >= 2 and parts[-1].isdigit():
                    # 移除最后一个数字部分
                    base_name = '-'.join(parts[:-1])
            elif len(parts) >= 3:
                # Deployment Pod格式：base-name-deployment-hash-pod-suffix
                # 移除最后两个部分（deployment hash和pod suffix）
                base_name = '-'.join(parts[:-2])
            
            # 对于Pod实例，JOB ID显示不带前缀的Pod名称，NAME显示yaml中的原始名称
            display_job_id = remove_prefix(job['name'])
            print(f"{display_job_id:<55} {base_name:<20} {job_type:<15} {status:<10} {age:<10}")
        
        return 0
    except Exception as e:
        print(f"❌ Error getting jobs: {e}")
        return 1


def delete_job_command(args):
    """删除作业命令"""
    try:
        client = JobClient()
        resource_type = None
        resource_name = None
        original_resource_name = None
        force = getattr(args, 'force', False)
        
        # 处理通过job_name删除作业的情况
        job_name = getattr(args, 'job_name', None)
        if job_name:
            # delete job <job_name> 命令
            resource_name = job_name
            original_resource_name = resource_name
        elif args.file:
            # delete -f <yaml_file> 命令
            resource_type = None
            resource_name = None
            original_resource_name = None
            
            try:
                # 尝试完整解析（兼容旧逻辑）
                parsed_obj = BaseParser.parse_yaml_file(args.file)
                resource_type = parsed_obj.kind
                
                if resource_type in ["pool", "resource"]:
                    # 资源池处理
                    if hasattr(parsed_obj, 'metadata') and hasattr(parsed_obj.metadata, 'name'):
                        resource_name = parsed_obj.metadata.name
                    elif hasattr(parsed_obj, 'pool') and hasattr(parsed_obj.pool, 'name'):
                        resource_name = parsed_obj.pool.name
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                elif resource_type in ["training", "inference", "notebook", "compute"]:
                    # 任务处理
                    if hasattr(parsed_obj, 'job') and hasattr(parsed_obj.job, 'name'):
                        resource_name = parsed_obj.job.name
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                    original_resource_name = resource_name
            except Exception as e:
                # 完整解析失败，尝试简单解析YAML获取必要信息
                import yaml
                with open(args.file, 'r') as f:
                    yaml_dict = yaml.safe_load(f)
                resource_type = yaml_dict['kind']
                
                if resource_type in ["pool", "resource"]:
                    # 资源池处理
                    if 'metadata' in yaml_dict and 'name' in yaml_dict['metadata']:
                        resource_name = yaml_dict['metadata']['name']
                    elif 'pool' in yaml_dict and 'name' in yaml_dict['pool']:
                        resource_name = yaml_dict['pool']['name']
                    else:
                        resource_name = args.file.replace('.yaml', '').replace('.yml', '')
                elif resource_type in ["training", "inference", "notebook", "compute"]:
                    # 任务处理
                    resource_name = yaml_dict['job']['name']
                    original_resource_name = resource_name
            
            # 处理资源池删除
            if resource_type in ["pool", "resource"]:
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
            print("❌ 必须提供YAML文件路径 (-f/--file) 或作业名称")
            return 1
        
        # 处理作业删除
        success = False
        
        # 获取所有作业列表，用于查询实际的作业类型
        # 这里需要获取Deployment/StatefulSet级别资源，而不是Pod实例
        all_jobs = client.list_jobs(args.namespace, include_pods=False)
        found_job = None
        
        # 在所有作业中查找匹配的作业
        for job in all_jobs:
            job_name = job['name']
            # 检查是否匹配原始名称（不带前缀）
            if remove_prefix(job_name) == resource_name:
                found_job = job
                break
        
        if found_job:
            # 从找到的作业中获取实际的作业类型和名称
            actual_job_type = found_job['labels'].get('g8s.host/job-type', 'unknown')
            actual_job_name = found_job['name']
            
            # 根据实际作业类型调用相应的删除方法（删除整个Deployment/StatefulSet/Job）
            if actual_job_type == "training":
                # Training任务：删除Job
                success = client.delete_job(actual_job_name, args.namespace, force)
            elif actual_job_type == "inference" or actual_job_type == "compute":
                # Inference或Compute任务：删除Deployment和Service
                # 生成完整Service名称
                service_name = f"g8s-host-svc-{resource_name}"
                # 删除Deployment
                deployment_deleted = client.delete_deployment(actual_job_name, args.namespace, force)
                # 删除Service
                service_deleted = client.delete_service(service_name, args.namespace)
                success = deployment_deleted and service_deleted
            elif actual_job_type == "notebook":
                # Notebook任务：删除StatefulSet和Service
                # 生成完整Service名称
                service_name = f"g8s-host-svc-{resource_name}"
                # 删除StatefulSet
                statefulset_deleted = client.delete_statefulset(actual_job_name, args.namespace, force)
                # 删除Service
                service_deleted = client.delete_service(service_name, args.namespace)
                success = statefulset_deleted and service_deleted
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
        log_client = LogClient()
        job_client = JobClient()
        
        # 处理Pod名称，确保使用完整的带前缀名称
        pod_name = args.job_name
        
        # 如果Pod名称不带有前缀，尝试获取作业类型并添加正确的前缀
        if not pod_name.startswith("g8s-host-"):
            # 获取所有作业列表，查找对应的作业类型
            all_jobs = job_client.list_jobs(args.namespace, include_pods=True)
            found = False
            for job in all_jobs:
                if remove_prefix(job['name']) == pod_name:
                    # 找到匹配的作业，获取其完整名称
                    pod_name = job['name']
                    found = True
                    break
            
            # 如果没有找到匹配的作业，尝试使用默认的compute前缀构建完整名称
            if not found:
                # 尝试使用compute前缀构建完整名称
                pod_name = f"g8s-host-compute-{pod_name}"
        
        if args.follow:
            # 使用流式日志，持续获取
            logs = log_client.stream_job_logs(args.job_name, namespace=args.namespace, pod_name=pod_name)
            for log in logs:
                print(log)
        else:
            # 只获取一次日志
            logs = log_client.get_job_logs(args.job_name, namespace=args.namespace, tail=100, pod_name=pod_name)
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
            # 获取所有作业列表，包括Pod实例，用于查询实际的作业
            all_jobs = client.list_jobs(args.namespace, include_pods=True)
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
        
        # 获取并显示访问方式
        job_type = job.get('labels', {}).get('g8s.host/job-type', '')
        if job_type in ['inference', 'compute', 'notebook']:
            print("\n🌐 Access Methods:")
            
            # 获取完整作业名称
            full_job_name = job.get('name', '')
            base_job_name = remove_prefix(full_job_name)
            
            # 提取服务基础名称
            service_base_name = base_job_name
            
            # 处理不同作业类型的服务名称提取
            if job_type == 'notebook':
                # StatefulSet Pod格式：base-name-index (如new-test-notebook-job-0)
                parts = service_base_name.split('-')
                if len(parts) >= 2 and parts[-1].isdigit():
                    # 移除最后一个数字部分
                    service_base_name = '-'.join(parts[:-1])
            elif len(service_base_name.split('-')) >= 3:
                # Deployment Pod格式：base-name-deployment-hash-pod-suffix
                service_base_name = '-'.join(service_base_name.split('-')[:-2])
            
            # 先获取Service信息，用于获取端口
            service_data = None
            service_found = True
            try:
                import subprocess
                import json
                
                service_cmd = f"kubectl get svc g8s-host-svc-{service_base_name} -n g8s-host -o json"
                service_output = subprocess.check_output(service_cmd, shell=True, text=True)
                service_data = json.loads(service_output)
            except Exception as e:
                service_found = False
            
            # 方式1: 通过Pod IP访问
            print(f"   1. Pod IP Access:")
            try:
                import subprocess
                import json
                
                # 直接获取指定Pod的信息，而不是所有匹配的Pod
                pod_cmd = f"kubectl get pod {full_job_name} -n g8s-host -o json"
                pod_output = subprocess.check_output(pod_cmd, shell=True, text=True)
                pod_data = json.loads(pod_output)
                
                # 检查Pod状态
                pod_status = pod_data['status']['phase']
                if pod_status == 'Running':
                    # 只在Running状态下获取并显示Pod IP
                    pod_ip = pod_data['status'].get('podIP', 'N/A')
                    if service_found and service_data:
                        # 获取Service的端口信息
                        target_port = service_data['spec']['ports'][0]['targetPort'] if service_data['spec']['ports'] else 'N/A'
                        service_port = service_data['spec']['ports'][0]['port'] if service_data['spec']['ports'] else 'N/A'
                        pod_port = target_port if target_port != 'N/A' else service_port
                        print(f"      - Pod IP: {pod_ip}")
                        print(f"      - Port: {pod_port}")
                        print(f"      - Access: curl http://{pod_ip}:{pod_port}")
                    else:
                        print(f"      - Pod IP: {pod_ip}")
                else:
                    # Pod不是Running状态，不显示IP
                    print(f"      - Pod is {pod_status}, no IP available")
            except subprocess.CalledProcessError:
                print(f"      - Pod {full_job_name} not found")
            except Exception as e:
                print(f"      - Failed to get pod info: {e}")
            
            # 方式2: 通过NodePort访问
            print(f"   2. NodePort Access:")
            if not service_found:
                # 服务不存在，显示友好信息
                print(f"      - Service not available for this job")
            else:
                try:
                    import subprocess
                    import json
                    
                    if service_data:
                        # 获取Service的端口信息
                        node_port = service_data['spec']['ports'][0]['nodePort'] if service_data['spec']['ports'] and 'nodePort' in service_data['spec']['ports'][0] else 'N/A'
                        
                        # 获取Node IP
                        node_cmd = f"kubectl get nodes -o json"
                        node_output = subprocess.check_output(node_cmd, shell=True, text=True)
                        node_data = json.loads(node_output)
                        node_ip = node_data['items'][0]['status']['addresses'][0]['address'] if node_data['items'] else 'N/A'
                        
                        # 检查Pod状态，如果Pod不是Running，则NodePort访问不可用
                        pod_cmd = f"kubectl get pod {full_job_name} -n g8s-host -o json"
                        pod_output = subprocess.check_output(pod_cmd, shell=True, text=True)
                        pod_data = json.loads(pod_output)
                        pod_status = pod_data['status']['phase']
                        
                        if pod_status == 'Running':
                            print(f"      - Node IP: {node_ip}")
                            print(f"      - NodePort: {node_port}")
                            if node_port != 'N/A':
                                print(f"      - Access: curl http://{node_ip}:{node_port}")
                            else:
                                print(f"      - NodePort not available")
                        else:
                            # Pod不是Running状态，NodePort访问不可用
                            print(f"      - Pod is {pod_status}, NodePort access unavailable")
                    else:
                        print(f"      - No service found for this job")
                except Exception as e:
                    print(f"      - Failed to get service info: {e}")
        
        return 0
    except Exception as e:
        print(f"❌ Error describing job: {e}")
        return 1
