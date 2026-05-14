"""Unit tests for ``gpuctl.backend.ssh.runtime``: pure command builders."""

from __future__ import annotations

from gpuctl.backend.ssh import runtime


class TestContainerName:
    def test_short(self, training_spec):
        assert runtime.container_name(training_spec) == "gpuctl-acme-training-demo-train"

    def test_lowercased_and_sanitised(self, training_spec):
        spec = training_spec.__class__(
            **{**training_spec.__dict__, "name": "DEMO Train!", "namespace": "ns/1"}
        )
        n = runtime.container_name(spec)
        assert n.startswith("gpuctl-ns-1-training-demo-train-")
        assert all(c.isalnum() or c in "_.-" for c in n)

    def test_long_name_truncated_with_hash(self):
        from gpuctl.backend.base import JobSpec
        from gpuctl.constants import Kind, Priority

        spec = JobSpec(
            name="a" * 80,
            namespace="default",
            kind=Kind.TRAINING,
            image="img",
            command=(),
            args=(),
            env=(),
            cpu_millicores=1000,
            memory_bytes=1 << 30,
            gpu_count=0,
            gpu_type=None,
            pool=None,
            replicas=1,
            port=None,
            health_check=None,
            workdirs=(),
            priority=Priority.MEDIUM,
            labels=(),
            annotations=(),
            image_pull_secret=None,
            long_running=False,
            restart_policy="Never",
        )
        n = runtime.container_name(spec)
        assert len(n) <= 63
        # 8-char hex suffix preceded by '-'
        assert n[-9] == "-"
        assert all(c in "0123456789abcdef" for c in n[-8:])


class TestBuildRunCommand:
    def test_training_shape(self, training_spec):
        cmd = runtime.build_run_command(training_spec, name="gpuctl-acme-training-demo")
        assert cmd.startswith("docker run -d --rm=false --name gpuctl-acme-training-demo")
        assert "--cpus=8" in cmd
        assert "--memory=34359738368" in cmd
        assert "--gpus count=2" in cmd
        assert "-e NCCL_DEBUG=INFO" in cmd
        # No -p flag for non-service workloads.
        assert " -p " not in cmd
        # The image and full command come at the end.
        assert "hiyouga/llamafactory:0.9.4 bash -lc 'python train.py'" in cmd

    def test_managed_by_label_is_always_present(self, training_spec):
        cmd = runtime.build_run_command(training_spec, name="x")
        # shlex.quote returns shell-safe strings unquoted, so the label
        # appears bare. Matching either form keeps the test resilient.
        assert (
            "--label runwhere.ai/managed-by=gpuctl" in cmd
            or "--label 'runwhere.ai/managed-by=gpuctl'" in cmd
        )

    def test_long_running_adds_restart_and_port(self, training_spec):
        spec = training_spec.__class__(
            **{
                **training_spec.__dict__,
                "long_running": True,
                "restart_policy": "Always",
                "port": 8000,
            }
        )
        cmd = runtime.build_run_command(spec, name="x")
        assert "--restart=unless-stopped" in cmd
        assert "-p 8000:8000" in cmd

    def test_env_value_with_shell_metacharacters_is_quoted(self, training_spec):
        spec = training_spec.__class__(
            **{**training_spec.__dict__, "env": (("FOO", "a;rm -rf /"),)}
        )
        cmd = runtime.build_run_command(spec, name="x")
        # Shell-quoted so the dangerous payload becomes inert.
        assert "-e 'FOO=a;rm -rf /'" in cmd

    def test_volume_mounts(self, training_spec):
        cmd = runtime.build_run_command(training_spec, name="x")
        assert "-v /data:/data" in cmd
        assert "-v /output:/output" in cmd


class TestParseInspect:
    def test_running_container(self):
        sample = (
            '[{"Id":"abc","State":{"Status":"running","Running":true,'
            '"ExitCode":0,"StartedAt":"2026-05-14T01:00:00Z",'
            '"FinishedAt":"0001-01-01T00:00:00Z","Error":""}}]'
        )
        parsed = runtime.parse_inspect_state(sample)
        assert parsed["status"] == "running"
        assert parsed["running"] is True
        assert parsed["exit_code"] == 0
        assert parsed["id"] == "abc"

    def test_empty_or_invalid(self):
        assert runtime.parse_inspect_state("") == {}
        assert runtime.parse_inspect_state("not json") == {}
        assert runtime.parse_inspect_state("[]") == {}


class TestBuildAuxCommands:
    def test_inspect(self):
        assert runtime.build_inspect_command("c1") == "docker inspect c1"

    def test_logs_follow(self):
        assert runtime.build_logs_command("c1", tail=50, follow=True) == "docker logs -f --tail=50 c1"

    def test_logs_no_follow(self):
        assert runtime.build_logs_command("c1", tail=10, follow=False) == "docker logs --tail=10 c1"

    def test_rm(self):
        assert runtime.build_rm_command("c1") == "docker rm -f c1"

    def test_list_with_namespace(self):
        cmd = runtime.build_list_command(namespace="acme")
        assert cmd.startswith("docker ps -a --format")
        assert "--filter label=runwhere.ai/managed-by=gpuctl" in cmd
        assert "--filter label=runwhere.ai/namespace=acme" in cmd
