import unittest
from gpuctl.cli.job_mapper import _map_compute_job


class TestComputeJobMapper(unittest.TestCase):
    """测试compute作业映射函数"""

    def setUp(self):
        """设置测试数据"""
        # 基础映射数据
        self.base_mapped = {
            'kind': 'compute',
            'job': {
                'name': 'test-nginx',
                'namespace': 'default',
                'priority': 'medium',
                'description': 'Test job'
            }
        }

        # 带有哈希后缀的作业名称
        self.base_mapped_with_hash = {
            'kind': 'compute',
            'job': {
                'name': 'test-nginx-abc123',
                'namespace': 'default',
                'priority': 'medium',
                'description': 'Test job'
            }
        }

        # 基础Kubernetes资源数据
        self.base_job_data = {
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                'command': ['nginx', '-g', 'daemon off;'],
                                'image': 'nginx:latest',
                                'resources': {
                                    'limits': {
                                        'cpu': '1',
                                        'memory': '1G'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

    def test_map_compute_job_basic(self):
        """测试基本的compute作业映射"""
        # 调用映射函数
        result = _map_compute_job(self.base_job_data, self.base_mapped)

        # 验证结果
        self.assertEqual(result['kind'], 'compute')
        self.assertEqual(result['version'], 'v1')
        self.assertEqual(result['job']['name'], 'test-nginx')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'medium')
        self.assertEqual(result['job']['description'], 'Test job')
        self.assertEqual(result['environment']['image'], 'nginx:latest')
        self.assertEqual(result['environment']['command'], ['nginx', '-g', 'daemon off;'])
        self.assertEqual(result['service']['replicas'], 1)  # 默认值
        self.assertEqual(result['service']['port'], 8000)  # 默认值
        self.assertEqual(result['resources']['pool'], 'default')  # 默认值
        self.assertEqual(result['resources']['cpu'], '1')
        self.assertEqual(result['resources']['memory'], '1G')
        self.assertEqual(result['resources']['gpu'], 0)  # 默认值

    def test_map_compute_job_with_hash_suffix(self):
        """测试带有哈希后缀的compute作业映射"""
        # 调用映射函数
        result = _map_compute_job(self.base_job_data, self.base_mapped_with_hash)

        # 验证结果，作业名称应该移除哈希后缀
        self.assertEqual(result['job']['name'], 'test-nginx')

    def test_map_compute_job_with_args(self):
        """测试带有参数的compute作业映射"""
        # 创建带有参数的作业数据
        job_with_args = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'args': ['--arg1', 'value1', '--arg2', 'value2']
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_compute_job(job_with_args, self.base_mapped)

        # 验证结果，应该包含args字段
        self.assertIn('args', result['environment'])
        self.assertEqual(result['environment']['args'], ['--arg1', 'value1', '--arg2', 'value2'])

    def test_map_compute_job_with_env(self):
        """测试带有环境变量的compute作业映射"""
        # 创建带有环境变量的作业数据
        job_with_env = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'env': [
                                    {'name': 'ENV_VAR1', 'value': 'value1'},
                                    {'name': 'ENV_VAR2', 'value': 'value2'}
                                ]
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_compute_job(job_with_env, self.base_mapped)

        # 验证结果，应该包含env字段
        self.assertIn('env', result['environment'])
        self.assertEqual(len(result['environment']['env']), 2)
        self.assertEqual(result['environment']['env'][0]['name'], 'ENV_VAR1')
        self.assertEqual(result['environment']['env'][0]['value'], 'value1')
        self.assertEqual(result['environment']['env'][1]['name'], 'ENV_VAR2')
        self.assertEqual(result['environment']['env'][1]['value'], 'value2')

    def test_map_compute_job_with_health_check(self):
        """测试带有健康检查的compute作业映射"""
        # 创建带有健康检查的作业数据
        job_with_health_check = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'livenessProbe': {
                                    'httpGet': {
                                        'path': '/health',
                                        'port': 8000
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_compute_job(job_with_health_check, self.base_mapped)

        # 验证结果，应该包含healthCheck字段
        self.assertIn('healthCheck', result['service'])
        self.assertEqual(result['service']['healthCheck'], '/health')

    def test_map_compute_job_with_workdirs(self):
        """测试带有工作目录的compute作业映射"""
        # 创建带有工作目录的作业数据
        job_with_workdirs = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            self.base_job_data['spec']['template']['spec']['containers'][0]
                        ],
                        'volumes': [
                            {
                                'hostPath': {
                                    'path': '/home/data/'
                                },
                                'name': 'workdir-0'
                            },
                            {
                                'hostPath': {
                                    'path': '/var/log/'
                                },
                                'name': 'workdir-1'
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_compute_job(job_with_workdirs, self.base_mapped)

        # 验证结果，应该包含storage.workdirs字段
        self.assertIn('storage', result)
        self.assertIn('workdirs', result['storage'])
        self.assertEqual(len(result['storage']['workdirs']), 2)
        self.assertEqual(result['storage']['workdirs'][0]['path'], '/home/data/')
        self.assertEqual(result['storage']['workdirs'][1]['path'], '/var/log/')

    def test_map_compute_job_with_ports(self):
        """测试带有端口的compute作业映射"""
        # 创建带有端口的作业数据
        job_with_ports = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'ports': [
                                    {'containerPort': 8080}
                                ]
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_compute_job(job_with_ports, self.base_mapped)

        # 验证结果，端口应该被正确提取
        self.assertEqual(result['service']['port'], 8080)

    def test_map_compute_job_with_replicas(self):
        """测试带有副本数的compute作业映射"""
        # 创建带有副本数的作业数据
        job_with_replicas = {
            **self.base_job_data,
            'spec': {
                'replicas': 3,
                'template': self.base_job_data['spec']['template']
            }
        }

        # 调用映射函数
        result = _map_compute_job(job_with_replicas, self.base_mapped)

        # 验证结果，副本数应该被正确提取
        self.assertEqual(result['service']['replicas'], 3)

    def test_map_compute_job_with_gpu(self):
        """测试带有GPU的compute作业映射"""
        # 创建带有GPU的作业数据
        job_with_gpu = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'resources': {
                                    'limits': {
                                        'cpu': '1',
                                        'memory': '1G',
                                        'nvidia.com/gpu': '1'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_compute_job(job_with_gpu, self.base_mapped)

        # 验证结果，GPU应该被正确提取
        self.assertEqual(result['resources']['gpu'], '1')


if __name__ == '__main__':
    unittest.main()
