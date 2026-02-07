from typing import Dict, Any, Optional, List, Union
from kubernetes import client


def _format_cpu_value(cpu: Any) -> Union[int, str]:
    """
    格式化 CPU 值，将纯数字字符串转换为整数
    例如: '1' -> 1, '100m' -> '100m', '0.5' -> '0.5'
    """
    if cpu is None:
        return 1
    if isinstance(cpu, int):
        return cpu
    if isinstance(cpu, str):
        # 尝试转换为整数
        try:
            return int(cpu)
        except ValueError:
            pass
        # 尝试转换为浮点数（如果是纯数字）
        try:
            float_val = float(cpu)
            # 如果是整数形式的浮点数（如 1.0），返回整数
            if float_val == int(float_val):
                return int(float_val)
            return cpu  # 保持原始字符串
        except ValueError:
            pass
    return cpu


def extract_container_image(job: Dict[str, Any]) -> str:
    """
    从Kubernetes资源中提取容器镜像
    """
    try:
        containers = get_containers_spec(job)
        return containers[0].get('image', 'N/A') if containers else 'N/A'
    except Exception:
        return 'N/A'


def extract_command(job: Dict[str, Any]) -> List[str]:
    """
    从Kubernetes资源中提取容器命令
    """
    try:
        containers = get_containers_spec(job)
        return containers[0].get('command', []) if containers else []
    except Exception:
        return []


def extract_args(job: Dict[str, Any]) -> List[str]:
    """
    从Kubernetes资源中提取容器参数
    """
    try:
        containers = get_containers_spec(job)
        return containers[0].get('args', []) if containers else []
    except Exception:
        return []


def extract_env(job: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    从Kubernetes资源中提取环境变量
    """
    try:
        containers = get_containers_spec(job)
        if not containers:
            return []
        env_vars = containers[0].get('env', [])
        # 转换为标准格式
        formatted_env = []
        for env in env_vars:
            if isinstance(env, dict):
                # 检查是否是错误格式的env（name和value作为键）
                if 'name' in env and 'value' in env:
                    formatted_env.append(env)
                else:
                    # 处理错误格式
                    name = None
                    value = None
                    for key, val in env.items():
                        if key == 'name':
                            name = val
                        elif key == 'value':
                            value = val
                    if name and value:
                        formatted_env.append({'name': name, 'value': value})
        return formatted_env
    except Exception:
        return []


def extract_resources(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    从Kubernetes资源中提取资源配置
    """
    try:
        containers = get_containers_spec(job)
        if not containers:
            return {'cpu': '1', 'memory': '1G', 'gpu': 0}
        resources = containers[0].get('resources', {})
        limits = resources.get('limits', {})
        return {
            'cpu': limits.get('cpu', '1'),
            'memory': limits.get('memory', '1G'),
            'gpu': limits.get('nvidia.com/gpu', 0)
        }
    except Exception:
        return {'cpu': '1', 'memory': '1G', 'gpu': 0}


def extract_labels(job: Dict[str, Any]) -> Dict[str, str]:
    """
    从Kubernetes资源中提取标签
    """
    try:
        # 尝试从metadata.labels提取（Pod、Deployment等资源）
        if 'metadata' in job and isinstance(job['metadata'], dict):
            return job['metadata'].get('labels', {})
        # 尝试直接从labels提取（兼容性）
        return job.get('labels', {})
    except Exception:
        return {}


def extract_annotations(job: Dict[str, Any]) -> Dict[str, str]:
    """
    从Kubernetes资源中提取注解
    """
    try:
        # 尝试从metadata.annotations提取
        if 'metadata' in job and isinstance(job['metadata'], dict):
            return job['metadata'].get('annotations', {})
        # 尝试直接从annotations提取（兼容性）
        return job.get('annotations', {})
    except Exception:
        return {}


def get_containers_spec(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    获取容器规格列表，处理不同资源类型的结构差异
    """
    try:
        # 检查是否是Pod资源（直接在spec.containers）
        if 'spec' in job and 'containers' in job['spec']:
            return job['spec']['containers']
        # 检查是否是Deployment/StatefulSet资源（在spec.template.spec.containers）
        elif 'spec' in job and 'template' in job['spec'] and 'spec' in job['spec']['template'] and 'containers' in job['spec']['template']['spec']:
            return job['spec']['template']['spec']['containers']
        return []
    except Exception:
        return []


def get_pod_spec(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取Pod规格，处理不同资源类型的结构差异
    """
    try:
        # 检查是否是Deployment/StatefulSet资源（在spec.template.spec）
        if 'spec' in job and 'template' in job['spec'] and 'spec' in job['spec']['template']:
            return job['spec']['template']['spec']
        # 检查是否是Pod资源（直接在spec）
        elif 'spec' in job:
            return job['spec']
        return {}
    except Exception:
        return {}


def extract_replicas(job: Dict[str, Any]) -> int:
    """
    从Kubernetes资源中提取副本数
    """
    try:
        return job.get('spec', {}).get('replicas', 1)
    except Exception:
        return 1


def extract_ports(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从Kubernetes资源中提取端口配置
    """
    try:
        containers = get_containers_spec(job)
        return containers[0].get('ports', []) if containers else []
    except Exception:
        return []


def extract_health_check(job: Dict[str, Any]) -> str:
    """
    从Kubernetes资源中提取健康检查路径
    """
    try:
        containers = get_containers_spec(job)
        if not containers:
            return ''
        return containers[0].get('livenessProbe', {}).get('httpGet', {}).get('path', '')
    except Exception:
        return ''


def extract_workdirs(job: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    从Kubernetes资源中提取工作目录配置
    """
    try:
        pod_spec = get_pod_spec(job)
        volumes = pod_spec.get('volumes', [])
        workdirs = []
        for volume in volumes:
            if 'hostPath' in volume:
                path = volume.get('hostPath', {}).get('path', '')
                if path:
                    workdirs.append({'path': path})
        return workdirs
    except Exception:
        return []


def extract_gpu_type(job: Dict[str, Any]) -> str:
    """
    从Kubernetes资源中提取GPU类型
    """
    try:
        pod_spec = get_pod_spec(job)
        return pod_spec.get('nodeSelector', {}).get('g8s.host/gpuType', '')
    except Exception:
        return ''


def map_k8s_to_gpuctl(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    将Kubernetes资源映射回gpuctl的YAML格式

    Args:
        job: 从Kubernetes API获取的作业资源字典

    Returns:
        Dict[str, Any]: 映射后的gpuctl YAML格式字典
    """
    # 提取标签和注解
    labels = extract_labels(job)
    annotations = extract_annotations(job)
    job_type = labels.get('g8s.host/job-type', 'unknown')

    # 基础映射 - 创建空字典
    mapped = {}

    # 按正确顺序添加键
    mapped['kind'] = job_type
    mapped['job'] = {
        'name': job.get('name', 'N/A'),
        'namespace': job.get('namespace', 'default'),
        'priority': labels.get('g8s.host/priority', 'medium'),
        'description': annotations.get('g8s.host/description', '')  # 从 annotation 中提取描述
    }
    
    # 根据作业类型进行特定映射
    if job_type == 'compute':
        mapped = _map_compute_job(job, mapped)
    elif job_type == 'inference':
        mapped = _map_inference_job(job, mapped)
    elif job_type == 'training':
        mapped = _map_training_job(job, mapped)
    elif job_type == 'notebook':
        mapped = _map_notebook_job(job, mapped)
    
    return mapped


def _map_compute_job(job: Dict[str, Any], mapped: Dict[str, Any]) -> Dict[str, Any]:
    """
    映射compute类型的作业
    """
    # 提取基础作业名称（移除哈希后缀）
    base_job_name = mapped['job']['name']
    if '-' in base_job_name:
        parts = base_job_name.split('-')
        if len(parts) >= 3:
            third_part = parts[2] if len(parts) >= 3 else ''
            if third_part.isalnum() and len(third_part) >= 5:
                # 这是一个带有哈希后缀的Pod名称，提取基础名称
                base_job_name = '-'.join(parts[:2])
    
    # 提取数据
    image = extract_container_image(job)
    command = extract_command(job)
    args = extract_args(job)
    env = extract_env(job)
    resources = extract_resources(job)
    replicas = extract_replicas(job)
    ports = extract_ports(job)
    health_check = extract_health_check(job)
    workdirs = extract_workdirs(job)
    labels = extract_labels(job)
    
    # 提取端口 - 优先从 label 中获取，其次从 container ports 中获取
    port = labels.get('g8s.host/port')  # 优先从 label 获取
    if port:
        try:
            port = int(port)
        except (ValueError, TypeError):
            port = None
    if not port and ports:
        port = ports[0].get('containerPort', 8000)
    if not port:
        port = 8000  # 默认端口
    
    # 创建有序映射
    ordered_mapped = {
        'kind': mapped['kind'],
        'version': 'v1',
        'job': {
            'name': base_job_name,
            'namespace': mapped['job']['namespace'],
            'priority': mapped['job']['priority'],
            'description': mapped['job'].get('description', 'Test compute job')
        },
        'environment': {
            'image': image,
            'command': command
        },
        'service': {
            'replicas': replicas,
            'port': port
        },
        'resources': {
            'pool': labels.get('g8s.host/pool', 'default'),
            'gpu': resources.get('gpu', 0),
            'cpu': _format_cpu_value(resources.get('cpu', '1')),
            'memory': resources.get('memory', '1G')
        }
    }
    
    # 添加可选字段
    if args:
        ordered_mapped['environment']['args'] = args
    
    if env:
        ordered_mapped['environment']['env'] = env
    
    if health_check:
        ordered_mapped['service']['healthCheck'] = health_check
    
    if workdirs:
        ordered_mapped['storage'] = {
            'workdirs': workdirs
        }
    
    return ordered_mapped


def _map_inference_job(job: Dict[str, Any], mapped: Dict[str, Any]) -> Dict[str, Any]:
    """
    映射inference类型的作业
    """
    # 提取基础作业名称（移除哈希后缀）
    base_job_name = mapped['job']['name']
    if '-' in base_job_name:
        parts = base_job_name.split('-')
        if len(parts) >= 3:
            third_part = parts[2] if len(parts) >= 3 else ''
            if third_part.isalnum() and len(third_part) >= 5:
                # 这是一个带有哈希后缀的Pod名称，提取基础名称
                base_job_name = '-'.join(parts[:2])
    
    # 提取数据
    image = extract_container_image(job)
    command = extract_command(job)
    args = extract_args(job)
    env = extract_env(job)
    resources = extract_resources(job)
    replicas = extract_replicas(job)
    ports = extract_ports(job)
    health_check = extract_health_check(job)
    workdirs = extract_workdirs(job)
    labels = extract_labels(job)
    
    # 提取端口
    port = 8000  # 默认端口
    if ports:
        port = ports[0].get('containerPort', 8000)
    
    # 创建有序映射
    ordered_mapped = {
        'kind': mapped['kind'],
        'version': 'v0.1',
        'job': {
            'name': base_job_name,
            'namespace': mapped['job']['namespace'],
            'priority': mapped['job']['priority'],
            'description': mapped['job'].get('description', '测试推理任务')
        },
        'environment': {
            'image': image,
            'command': command
        },
        'service': {
            'replicas': replicas,
            'port': port
        },
        'resources': {
            'pool': labels.get('g8s.host/pool', 'default'),
            'gpu': resources.get('gpu', 0),
            'cpu': _format_cpu_value(resources.get('cpu', '1')),
            'memory': resources.get('memory', '2Gi'),
            'gpuShare': '2Gi'  # 默认值
        }
    }
    
    # 添加可选字段
    if args:
        ordered_mapped['environment']['args'] = args
    
    if env:
        ordered_mapped['environment']['env'] = env
    
    if health_check:
        ordered_mapped['service']['healthCheck'] = health_check
    
    if workdirs:
        ordered_mapped['storage'] = {
            'workdirs': workdirs
        }
    
    return ordered_mapped


def _map_training_job(job: Dict[str, Any], mapped: Dict[str, Any]) -> Dict[str, Any]:
    """
    映射training类型的作业
    """
    # 提取基础作业名称（移除哈希后缀）
    base_job_name = mapped['job']['name']
    if '-' in base_job_name:
        parts = base_job_name.split('-')
        if len(parts) >= 3:
            third_part = parts[2] if len(parts) >= 3 else ''
            if third_part.isalnum() and len(third_part) >= 5:
                # 这是一个带有哈希后缀的Pod名称，提取基础名称
                base_job_name = '-'.join(parts[:2])
    
    # 提取数据
    image = extract_container_image(job)
    command = extract_command(job)
    args = extract_args(job)
    env = extract_env(job)
    resources = extract_resources(job)
    workdirs = extract_workdirs(job)
    labels = extract_labels(job)
    gpu_type = extract_gpu_type(job)
    
    # 创建有序映射
    ordered_mapped = {
        'kind': mapped['kind'],
        'version': 'v0.1',
        'job': {
            'name': base_job_name,
            'namespace': mapped['job']['namespace'],
            'priority': mapped['job']['priority'],
            'description': mapped['job'].get('description', '测试训练任务')
        },
        'environment': {
            'image': image,
            'command': command
        },
        'resources': {
            'pool': labels.get('g8s.host/pool', 'training-pool'),
            'gpu': resources.get('gpu', 2),
            'gpuType': gpu_type,
            'cpu': _format_cpu_value(resources.get('cpu', '8')),
            'memory': resources.get('memory', '32Gi'),
            'gpuShare': '2Gi'  # 默认值
        }
    }

    # 添加可选字段
    if args:
        ordered_mapped['environment']['args'] = args

    if env:
        ordered_mapped['environment']['env'] = env

    if workdirs:
        ordered_mapped['storage'] = {
            'workdirs': workdirs
        }
    
    return ordered_mapped


def _map_notebook_job(job: Dict[str, Any], mapped: Dict[str, Any]) -> Dict[str, Any]:
    """
    映射notebook类型的作业
    """
    # 提取基础作业名称（移除哈希后缀）
    base_job_name = mapped['job']['name']
    if '-' in base_job_name:
        parts = base_job_name.split('-')
        if len(parts) >= 3:
            third_part = parts[2] if len(parts) >= 3 else ''
            if third_part.isalnum() and len(third_part) >= 5:
                # 这是一个带有哈希后缀的Pod名称，提取基础名称
                base_job_name = '-'.join(parts[:2])
    
    # 提取数据
    image = extract_container_image(job)
    command = extract_command(job)
    args = extract_args(job)
    env = extract_env(job)
    resources = extract_resources(job)
    replicas = extract_replicas(job)
    ports = extract_ports(job)
    workdirs = extract_workdirs(job)
    labels = extract_labels(job)
    
    # 提取端口
    port = 8888  # 默认端口
    if ports:
        port = ports[0].get('containerPort', 8888)
    
    # 创建有序映射
    ordered_mapped = {
        'kind': mapped['kind'],
        'version': 'v0.1',
        'job': {
            'name': base_job_name,
            'namespace': mapped['job']['namespace'],
            'priority': mapped['job']['priority'],
            'description': mapped['job'].get('description', '测试Notebook任务')
        },
        'environment': {
            'image': image,
            'command': command
        },
        'service': {
            'port': port
        },
        'resources': {
            'pool': labels.get('g8s.host/pool', 'default'),
            'gpu': resources.get('gpu', 0),
            'cpu': _format_cpu_value(resources.get('cpu', '1')),
            'memory': resources.get('memory', '2Gi'),
            'gpuShare': '2Gi'  # 默认值
        }
    }

    # 添加可选字段
    if args:
        ordered_mapped['environment']['args'] = args

    if env:
        ordered_mapped['environment']['env'] = env

    if workdirs:
        ordered_mapped['storage'] = {
            'workdirs': workdirs
        }

    return ordered_mapped


def format_mapped_yaml(mapped: Dict[str, Any]) -> str:
    """
    格式化映射后的字典为YAML格式的字符串
    
    Args:
        mapped: 映射后的gpuctl YAML格式字典
    
    Returns:
        str: 格式化后的YAML字符串
    """
    import yaml
    return yaml.dump(mapped, default_flow_style=False, sort_keys=False)


def get_original_yaml_content(job: Dict[str, Any]) -> str:
    """
    获取原始YAML内容的字符串表示
    
    Args:
        job: 从Kubernetes API获取的作业资源字典
    
    Returns:
        str: 原始YAML内容的字符串表示
    """
    mapped = map_k8s_to_gpuctl(job)
    return format_mapped_yaml(mapped)
