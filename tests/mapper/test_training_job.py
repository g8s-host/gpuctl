import unittest
from gpuctl.cli.job_mapper import _map_training_job


class TestTrainingJobMapper(unittest.TestCase):
    """测试training作业映射函数"""

    def setUp(self):
        """设置测试数据"""
        # 基础映射数据
        self.base_mapped = {
            'kind': 'training',
            'job': {
                'name': 'test-training',
                'namespace': 'default',
                'priority': 'high',
                'description': 'Test job'
            }
        }

        # 带有哈希后缀的作业名称
        self.base_mapped_with_hash = {
            'kind': 'training',
            'job': {
                'name': 'test-training-abc123',
                'namespace': 'default',
                'priority': 'high',
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
                                'command': ['llama-factory-cli', 'train'],
                                'image': 'hiyouga/llamafactory:0.9.4',
                                'resources': {
                                    'limits': {
                                        'cpu': '8',
                                        'memory': '32Gi',
                                        'nvidia.com/gpu': '2'
                                    }
                                }
                            }
                        ],
                        'nodeSelector': {
                            'g8s.host/gpuType': 'a10-24g'
                        }
                    }
                }
            }
        }

    def test_map_training_job_basic(self):
        """测试基本的training作业映射"""
        # 调用映射函数
        result = _map_training_job(self.base_job_data, self.base_mapped)

        # 验证结果
        self.assertEqual(result['kind'], 'training')
        self.assertEqual(result['version'], 'v0.1')
        self.assertEqual(result['job']['name'], 'test-training')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'high')
        self.assertEqual(result['job']['description'], 'Test job')
        self.assertEqual(result['environment']['image'], 'hiyouga/llamafactory:0.9.4')
        self.assertEqual(result['environment']['command'], ['llama-factory-cli', 'train'])
        self.assertEqual(result['resources']['pool'], 'training-pool')  # 默认值
        self.assertEqual(result['resources']['gpu'], '2')
        self.assertEqual(result['resources']['gpuType'], 'a10-24g')
        self.assertEqual(result['resources']['cpu'], 8)
        self.assertEqual(result['resources']['memory'], '32Gi')
        self.assertEqual(result['resources']['gpuShare'], '2Gi')  # 默认值

    def test_map_training_job_with_hash_suffix(self):
        """测试带有哈希后缀的training作业映射"""
        # 调用映射函数
        result = _map_training_job(self.base_job_data, self.base_mapped_with_hash)

        # 验证结果，作业名称应该移除哈希后缀
        self.assertEqual(result['job']['name'], 'test-training')

    def test_map_training_job_with_args(self):
        """测试带有参数的training作业映射"""
        # 创建带有参数的作业数据
        job_with_args = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                **self.base_job_data['spec']['template']['spec']['containers'][0],
                                'args': ['--stage', 'sft', '--model_name_or_path', '/models/qwen2-7b']
                            }
                        ],
                        'nodeSelector': self.base_job_data['spec']['template']['spec']['nodeSelector']
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_training_job(job_with_args, self.base_mapped)

        # 验证结果，应该包含args字段
        self.assertIn('args', result['environment'])
        self.assertEqual(result['environment']['args'], ['--stage', 'sft', '--model_name_or_path', '/models/qwen2-7b'])

    def test_map_training_job_with_env(self):
        """测试带有环境变量的training作业映射"""
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
                                    {'name': 'NVIDIA_FLASH_ATTENTION', 'value': '1'},
                                    {'name': 'LLAMA_FACTORY_CACHE', 'value': '/cache/llama-factory'}
                                ]
                            }
                        ],
                        'nodeSelector': self.base_job_data['spec']['template']['spec']['nodeSelector']
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_training_job(job_with_env, self.base_mapped)

        # 验证结果，应该包含env字段
        self.assertIn('env', result['environment'])
        self.assertEqual(len(result['environment']['env']), 2)
        self.assertEqual(result['environment']['env'][0]['name'], 'NVIDIA_FLASH_ATTENTION')
        self.assertEqual(result['environment']['env'][0]['value'], '1')
        self.assertEqual(result['environment']['env'][1]['name'], 'LLAMA_FACTORY_CACHE')
        self.assertEqual(result['environment']['env'][1]['value'], '/cache/llama-factory')

    def test_map_training_job_with_workdirs(self):
        """测试带有工作目录的training作业映射"""
        # 创建带有工作目录的作业数据
        job_with_workdirs = {
            **self.base_job_data,
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            self.base_job_data['spec']['template']['spec']['containers'][0]
                        ],
                        'nodeSelector': self.base_job_data['spec']['template']['spec']['nodeSelector'],
                        'volumes': [
                            {
                                'hostPath': {
                                    'path': '/datasets/alpaca-qwen.json'
                                },
                                'name': 'workdir-0'
                            },
                            {
                                'hostPath': {
                                    'path': '/models/qwen2-7b'
                                },
                                'name': 'workdir-1'
                            },
                            {
                                'hostPath': {
                                    'path': '/output/qwen2-sft'
                                },
                                'name': 'workdir-2'
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_training_job(job_with_workdirs, self.base_mapped)

        # 验证结果，应该包含storage.workdirs字段
        self.assertIn('storage', result)
        self.assertIn('workdirs', result['storage'])
        self.assertEqual(len(result['storage']['workdirs']), 3)
        self.assertEqual(result['storage']['workdirs'][0]['path'], '/datasets/alpaca-qwen.json')
        self.assertEqual(result['storage']['workdirs'][1]['path'], '/models/qwen2-7b')
        self.assertEqual(result['storage']['workdirs'][2]['path'], '/output/qwen2-sft')

    def test_map_training_job_without_gpu_type(self):
        """测试没有GPU类型的training作业映射"""
        # 创建没有GPU类型的作业数据
        job_without_gpu_type = {
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            self.base_job_data['spec']['template']['spec']['containers'][0]
                        ]
                        # 缺少nodeSelector
                    }
                }
            }
        }

        # 调用映射函数
        result = _map_training_job(job_without_gpu_type, self.base_mapped)

        # 验证结果，GPU类型应该为空字符串
        self.assertEqual(result['resources']['gpuType'], '')

    def test_map_training_job_with_labels(self):
        """测试带有标签的training作业映射"""
        # 创建带有标签的作业数据
        job_with_labels = {
            **self.base_job_data,
            'labels': {
                'g8s.host/pool': 'custom-training-pool'
            }
        }

        # 调用映射函数
        result = _map_training_job(job_with_labels, self.base_mapped)

        # 验证结果，应该使用标签中的pool值
        self.assertEqual(result['resources']['pool'], 'custom-training-pool')


if __name__ == '__main__':
    unittest.main()
