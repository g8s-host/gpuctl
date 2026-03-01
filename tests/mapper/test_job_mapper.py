import unittest
from gpuctl.cli.job_mapper import map_k8s_to_gpuctl


class TestJobMapper(unittest.TestCase):
    """测试作业映射函数"""

    def setUp(self):
        """设置测试数据"""
        # 基础测试数据
        self.base_job_data = {
            'name': 'test-job',
            'namespace': 'default'
        }

    def test_map_k8s_to_gpuctl_compute_job(self):
        """测试映射compute类型的作业"""
        # 创建一个compute类型的作业资源
        compute_job = {
            **self.base_job_data,
            'labels': {
                'g8s.host/job-type': 'compute',
                'g8s.host/pool': 'default',
                'g8s.host/priority': 'medium'
            },
            'annotations': {
                'g8s.host/description': 'Test compute job'
            },
            'spec': {
                'replicas': 1,
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

        # 调用映射函数
        result = map_k8s_to_gpuctl(compute_job)

        # 验证结果
        self.assertEqual(result['kind'], 'compute')
        self.assertEqual(result['job']['name'], 'test-job')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'medium')
        self.assertEqual(result['job']['description'], 'Test compute job')
        self.assertIn('environment', result)
        self.assertIn('service', result)
        self.assertIn('resources', result)

    def test_map_k8s_to_gpuctl_compute_job_without_description(self):
        """测试映射没有description的compute类型作业"""
        # 创建一个没有description的compute类型作业资源
        compute_job = {
            **self.base_job_data,
            'labels': {
                'g8s.host/job-type': 'compute',
                'g8s.host/pool': 'default',
                'g8s.host/priority': 'medium'
                # 缺少 g8s.host/description
            },
            'annotations': {},
            'spec': {
                'replicas': 1,
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

        # 调用映射函数
        result = map_k8s_to_gpuctl(compute_job)

        # 验证结果，description 应该是空字符串
        self.assertEqual(result['kind'], 'compute')
        self.assertEqual(result['job']['description'], '')

    def test_map_k8s_to_gpuctl_inference_job(self):
        """测试映射inference类型的作业"""
        # 创建一个inference类型的作业资源
        inference_job = {
            **self.base_job_data,
            'labels': {
                'g8s.host/job-type': 'inference',
                'g8s.host/pool': 'default',
                'g8s.host/priority': 'medium'
            },
            'spec': {
                'replicas': 1,
                'template': {
                    'spec': {
                        'containers': [
                            {
                                'command': ['python', '-m', 'vllm.entrypoints.openai.api_server'],
                                'image': 'vllm/vllm-openai:v0.12.0',
                                'resources': {
                                    'limits': {
                                        'cpu': '1',
                                        'memory': '2Gi'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = map_k8s_to_gpuctl(inference_job)

        # 验证结果
        self.assertEqual(result['kind'], 'inference')
        self.assertEqual(result['job']['name'], 'test-job')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'medium')
        self.assertIn('environment', result)
        self.assertIn('service', result)
        self.assertIn('resources', result)

    def test_map_k8s_to_gpuctl_training_job(self):
        """测试映射training类型的作业"""
        # 创建一个training类型的作业资源
        training_job = {
            **self.base_job_data,
            'labels': {
                'g8s.host/job-type': 'training',
                'g8s.host/pool': 'training-pool',
                'g8s.host/priority': 'high'
            },
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

        # 调用映射函数
        result = map_k8s_to_gpuctl(training_job)

        # 验证结果
        self.assertEqual(result['kind'], 'training')
        self.assertEqual(result['job']['name'], 'test-job')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'high')
        self.assertIn('environment', result)
        self.assertIn('resources', result)

    def test_map_k8s_to_gpuctl_notebook_job(self):
        """测试映射notebook类型的作业"""
        # 创建一个notebook类型的作业资源
        notebook_job = {
            **self.base_job_data,
            'labels': {
                'g8s.host/job-type': 'notebook',
                'g8s.host/pool': 'default',
                'g8s.host/priority': 'medium'
            },
            'spec': {
                'replicas': 1,
                'template': {
                    'spec': {
                        'containers': [
                            {
                                'command': ['jupyter-lab', '--ip=0.0.0.0'],
                                'image': 'jupyter/minimal-notebook:latest',
                                'resources': {
                                    'limits': {
                                        'cpu': '1',
                                        'memory': '2Gi'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

        # 调用映射函数
        result = map_k8s_to_gpuctl(notebook_job)

        # 验证结果
        self.assertEqual(result['kind'], 'notebook')
        self.assertEqual(result['job']['name'], 'test-job')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'medium')
        self.assertIn('environment', result)
        self.assertIn('service', result)
        self.assertIn('resources', result)

    def test_map_k8s_to_gpuctl_unknown_job_type(self):
        """测试映射未知类型的作业"""
        # 创建一个未知类型的作业资源
        unknown_job = {
            **self.base_job_data,
            'labels': {
                'g8s.host/priority': 'medium'
                # 缺少g8s.host/job-type标签
            }
        }

        # 调用映射函数
        result = map_k8s_to_gpuctl(unknown_job)

        # 验证结果
        self.assertEqual(result['kind'], 'unknown')
        self.assertEqual(result['job']['name'], 'test-job')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'medium')
        # 未知类型的作业应该只包含基础映射，不包含特定类型的字段
        self.assertNotIn('environment', result)
        self.assertNotIn('service', result)
        self.assertNotIn('resources', result)

    def test_map_k8s_to_gpuctl_missing_labels(self):
        """测试映射缺少标签的作业"""
        # 创建一个缺少标签的作业资源
        job_without_labels = {
            **self.base_job_data
            # 缺少labels字段
        }

        # 调用映射函数
        result = map_k8s_to_gpuctl(job_without_labels)

        # 验证结果
        self.assertEqual(result['kind'], 'unknown')
        self.assertEqual(result['job']['name'], 'test-job')
        self.assertEqual(result['job']['namespace'], 'default')
        self.assertEqual(result['job']['priority'], 'medium')  # 默认值


if __name__ == '__main__':
    unittest.main()
