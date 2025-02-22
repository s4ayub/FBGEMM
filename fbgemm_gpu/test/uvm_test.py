#!/usr/bin/env python3

# pyre-ignore-all-errors[56]

# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from typing import List

import fbgemm_gpu
import hypothesis.strategies as st
import torch

# pyre-ignore[21]
from fbgemm_gpu.uvm import cudaMemAdvise, cudaMemoryAdvise, cudaMemPrefetchAsync

open_source: bool = getattr(fbgemm_gpu, "open_source", False)

if open_source:
    # pyre-ignore[21]
    from test_utils import gpu_unavailable
else:
    from fbgemm_gpu.test.test_utils import gpu_unavailable

from hypothesis import Verbosity, given, settings

MAX_EXAMPLES = 40


class UvmTest(unittest.TestCase):
    @unittest.skipIf(*gpu_unavailable)
    @given(
        sizes=st.lists(st.integers(min_value=1, max_value=8), min_size=1, max_size=4),
        vanilla=st.booleans(),
    )
    @settings(verbosity=Verbosity.verbose, max_examples=MAX_EXAMPLES, deadline=None)
    def test_is_uvm_tensor(self, sizes: List[int], vanilla: bool) -> None:
        op = (
            torch.ops.fbgemm.new_managed_tensor
            if not vanilla
            else torch.ops.fbgemm.new_vanilla_managed_tensor
        )
        uvm_t = op(torch.empty(0, device="cuda:0", dtype=torch.float), sizes)
        assert torch.ops.fbgemm.is_uvm_tensor(uvm_t)
        assert torch.ops.fbgemm.uvm_storage(uvm_t)

    @unittest.skipIf(*gpu_unavailable)
    @given(
        sizes=st.lists(st.integers(min_value=1, max_value=8), min_size=1, max_size=4),
        vanilla=st.booleans(),
    )
    @settings(verbosity=Verbosity.verbose, max_examples=MAX_EXAMPLES, deadline=None)
    def test_uvm_to_cpu(self, sizes: List[int], vanilla: bool) -> None:
        op = (
            torch.ops.fbgemm.new_managed_tensor
            if not vanilla
            else torch.ops.fbgemm.new_vanilla_managed_tensor
        )

        uvm_t = op(torch.empty(0, device="cuda:0", dtype=torch.float), sizes)
        cpu_t = torch.ops.fbgemm.uvm_to_cpu(uvm_t)
        assert not torch.ops.fbgemm.is_uvm_tensor(cpu_t)
        assert torch.ops.fbgemm.uvm_storage(cpu_t)

        uvm_t.copy_(cpu_t)
        assert torch.ops.fbgemm.is_uvm_tensor(uvm_t)
        assert torch.ops.fbgemm.uvm_storage(uvm_t)

        # Test use of cpu tensor after freeing the uvm tensor
        del uvm_t
        cpu_t.mul_(42)

    def test_enum(self) -> None:
        # pyre-ignore[16]
        assert cudaMemoryAdvise.cudaMemAdviseSetAccessedBy.value == 5

    @unittest.skipIf(*gpu_unavailable)
    @given(
        sizes=st.lists(
            st.integers(min_value=1, max_value=(1024)), min_size=1, max_size=4
        ),
        vanilla=st.booleans(),
    )
    @settings(verbosity=Verbosity.verbose, max_examples=MAX_EXAMPLES, deadline=None)
    def test_cudaMemAdvise(self, sizes: List[int], vanilla: bool) -> None:
        op = (
            torch.ops.fbgemm.new_managed_tensor
            if not vanilla
            else torch.ops.fbgemm.new_vanilla_managed_tensor
        )
        uvm_t = op(torch.empty(0, device="cuda:0", dtype=torch.float), sizes)
        assert torch.ops.fbgemm.is_uvm_tensor(uvm_t)
        assert torch.ops.fbgemm.uvm_storage(uvm_t)

        # pyre-ignore[16]
        cudaMemAdvise(uvm_t, cudaMemoryAdvise.cudaMemAdviseSetAccessedBy)

    @unittest.skipIf(*gpu_unavailable)
    @given(
        sizes=st.lists(
            st.integers(min_value=1, max_value=(1024)), min_size=1, max_size=3
        ),
        vanilla=st.booleans(),
    )
    @settings(verbosity=Verbosity.verbose, max_examples=MAX_EXAMPLES, deadline=None)
    def test_cudaMemPrefetchAsync(self, sizes: List[int], vanilla: bool) -> None:
        op = (
            torch.ops.fbgemm.new_managed_tensor
            if not vanilla
            else torch.ops.fbgemm.new_vanilla_managed_tensor
        )
        uvm_t = op(torch.empty(0, device="cuda:0", dtype=torch.float), sizes)
        assert torch.ops.fbgemm.is_uvm_tensor(uvm_t)
        assert torch.ops.fbgemm.uvm_storage(uvm_t)

        cudaMemPrefetchAsync(uvm_t)

        torch.cuda.synchronize(torch.device("cuda:0"))

    @unittest.skipIf(*gpu_unavailable or torch.cuda.device_count() < 2)
    @given(
        sizes=st.lists(
            st.integers(min_value=1, max_value=(1024)), min_size=1, max_size=4
        ),
        vanilla=st.booleans(),
    )
    @settings(verbosity=Verbosity.verbose, max_examples=MAX_EXAMPLES, deadline=None)
    def test_uvm_to_device(self, sizes: List[int], vanilla: bool) -> None:
        op = (
            torch.ops.fbgemm.new_managed_tensor
            if not vanilla
            else torch.ops.fbgemm.new_vanilla_managed_tensor
        )
        uvm_t = op(torch.empty(0, device="cuda:0", dtype=torch.float), sizes)
        assert torch.ops.fbgemm.is_uvm_tensor(uvm_t)
        assert torch.ops.fbgemm.uvm_storage(uvm_t)

        # Reference uvm tensor from second cuda device
        device_prototype = torch.empty(0, device="cuda:1")
        second_t = torch.ops.fbgemm.uvm_to_device(uvm_t, device_prototype)

        assert torch.ops.fbgemm.is_uvm_tensor(second_t)
        assert torch.ops.fbgemm.uvm_storage(second_t)
        assert second_t.device == device_prototype.device

    @unittest.skipIf(*gpu_unavailable)
    @given(
        sizes=st.lists(
            st.integers(min_value=1, max_value=(1024)), min_size=1, max_size=4
        ),
        vanilla=st.booleans(),
    )
    @settings(verbosity=Verbosity.verbose, max_examples=MAX_EXAMPLES, deadline=None)
    def test_uvm_slice(self, sizes: List[int], vanilla: bool) -> None:
        op = (
            torch.ops.fbgemm.new_managed_tensor
            if not vanilla
            else torch.ops.fbgemm.new_vanilla_managed_tensor
        )
        uvm_t = op(torch.empty(0, device="cuda:0", dtype=torch.float), sizes)
        assert torch.ops.fbgemm.is_uvm_tensor(uvm_t)
        assert torch.ops.fbgemm.uvm_storage(uvm_t)

        # Reference uvm tensor from second cuda device
        second_t = uvm_t[0]

        assert torch.ops.fbgemm.is_uvm_tensor(second_t)
        assert torch.ops.fbgemm.uvm_storage(second_t)

    @unittest.skipIf(*gpu_unavailable)
    @given(
        sizes=st.lists(
            st.integers(min_value=1, max_value=(1024)), min_size=1, max_size=4
        ),
        vanilla=st.booleans(),
    )
    @settings(verbosity=Verbosity.verbose, max_examples=MAX_EXAMPLES, deadline=None)
    def test_uvm_memadviceDontFork(self, sizes: List[int], vanilla: bool) -> None:
        op = (
            torch.ops.fbgemm.new_managed_tensor
            if not vanilla
            else torch.ops.fbgemm.new_vanilla_managed_tensor
        )
        uvm_t = op(torch.empty(0, device="cuda:0", dtype=torch.float), sizes)
        assert torch.ops.fbgemm.is_uvm_tensor(uvm_t)
        assert torch.ops.fbgemm.uvm_storage(uvm_t)

        cpu_t = torch.ops.fbgemm.uvm_to_cpu(uvm_t)

        torch.ops.fbgemm.uvm_mem_advice_dont_fork(cpu_t)

    @unittest.skipIf(*gpu_unavailable)
    @given(
        sizes=st.lists(
            st.integers(min_value=1, max_value=(512)), min_size=1, max_size=3
        ),
        vanilla=st.booleans(),
    )
    @settings(verbosity=Verbosity.verbose, max_examples=MAX_EXAMPLES, deadline=None)
    def test_uvm_to_cpu_clone(self, sizes: List[int], vanilla: bool) -> None:
        op = (
            torch.ops.fb.new_managed_tensor
            if not vanilla
            else torch.ops.fb.new_vanilla_managed_tensor
        )
        uvm_t = op(torch.empty(0, device="cuda:0", dtype=torch.float), sizes)
        assert torch.ops.fb.is_uvm_tensor(uvm_t)
        assert torch.ops.fb.uvm_storage(uvm_t)

        cpu_clone = torch.ops.fb.uvm_to_cpu_clone(uvm_t)

        assert not torch.ops.fb.is_uvm_tensor(cpu_clone)
        assert not torch.ops.fb.uvm_storage(cpu_clone)


if __name__ == "__main__":
    unittest.main()
