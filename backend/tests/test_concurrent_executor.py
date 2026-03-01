"""Tests for ConcurrentExecutor including unit and integration tests."""

import asyncio
import pytest
from datetime import datetime
from typing import List, Optional, Callable, Dict, Any

from src.services.concurrent_executor import ConcurrentExecutor, ProcessingResult


class TestConcurrentExecutorBasic:
    """Basic unit tests for ConcurrentExecutor."""
    
    def test_initialization_with_default_values(self):
        """Test that executor initializes with default concurrency limits."""
        executor = ConcurrentExecutor()
        
        assert executor.max_file_concurrency == 10
        assert executor.max_worksheet_concurrency == 10
        assert executor._active_file_count == 0
        assert executor._active_worksheet_count == 0
    
    def test_initialization_with_custom_values(self):
        """Test that executor initializes with custom concurrency limits."""
        executor = ConcurrentExecutor(
            max_file_concurrency=5,
            max_worksheet_concurrency=3
        )
        
        assert executor.max_file_concurrency == 5
        assert executor.max_worksheet_concurrency == 3
    
    def test_get_active_counts_initial_state(self):
        """Test that active counts are zero initially."""
        executor = ConcurrentExecutor(max_file_concurrency=5, max_worksheet_concurrency=3)
        
        counts = executor.get_active_counts()
        
        assert counts["active_files"] == 0
        assert counts["active_worksheets"] == 0
        assert counts["max_files"] == 5
        assert counts["max_worksheets"] == 3
    
    @pytest.mark.asyncio
    async def test_process_files_with_empty_list(self):
        """Test processing empty file list."""
        executor = ConcurrentExecutor()
        
        async def dummy_process(item, callback):
            return item
        
        results = await executor.process_files_concurrently([], dummy_process)
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_process_worksheets_with_empty_list(self):
        """Test processing empty worksheet list."""
        executor = ConcurrentExecutor()
        
        async def dummy_process(item, callback):
            return item
        
        results = await executor.process_worksheets_concurrently([], dummy_process)
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_process_files_successful_execution(self):
        """Test successful processing of files."""
        executor = ConcurrentExecutor()
        items = [1, 2, 3, 4, 5]
        
        async def process_item(item, callback):
            await asyncio.sleep(0.01)  # Simulate work
            return item * 2
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 5
        assert all(r.success for r in results)
        assert [r.result for r in results] == [2, 4, 6, 8, 10]
    
    @pytest.mark.asyncio
    async def test_process_worksheets_successful_execution(self):
        """Test successful processing of worksheets."""
        executor = ConcurrentExecutor()
        items = ["ws1", "ws2", "ws3"]
        
        async def process_item(item, callback):
            await asyncio.sleep(0.01)  # Simulate work
            return f"processed_{item}"
        
        results = await executor.process_worksheets_concurrently(items, process_item)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.result for r in results] == ["processed_ws1", "processed_ws2", "processed_ws3"]
    
    @pytest.mark.asyncio
    async def test_process_files_with_errors(self):
        """Test that errors are captured in results."""
        executor = ConcurrentExecutor()
        items = [1, 2, 3, 4, 5]
        
        async def process_item(item, callback):
            if item == 3:
                raise ValueError(f"Error processing {item}")
            return item * 2
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 5
        assert sum(1 for r in results if r.success) == 4
        assert sum(1 for r in results if not r.success) == 1
        
        # Check the failed item
        failed = [r for r in results if not r.success][0]
        assert failed.item == 3
        assert isinstance(failed.error, ValueError)
    
    @pytest.mark.asyncio
    async def test_process_worksheets_with_errors(self):
        """Test that worksheet processing handles errors correctly."""
        executor = ConcurrentExecutor()
        items = ["ws1", "ws2", "ws3", "ws4"]
        
        async def process_item(item, callback):
            if item == "ws2":
                raise RuntimeError(f"Error processing {item}")
            return f"processed_{item}"
        
        results = await executor.process_worksheets_concurrently(items, process_item)
        
        assert len(results) == 4
        assert sum(1 for r in results if r.success) == 3
        assert sum(1 for r in results if not r.success) == 1
        
        # Check the failed item
        failed = [r for r in results if not r.success][0]
        assert failed.item == "ws2"
        assert isinstance(failed.error, RuntimeError)
    
    @pytest.mark.asyncio
    async def test_processing_result_duration_calculation(self):
        """Test that processing duration is calculated correctly."""
        executor = ConcurrentExecutor()
        items = [1]
        
        async def process_item(item, callback):
            await asyncio.sleep(0.1)  # Sleep for 100ms
            return item
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 1
        result = results[0]
        assert result.duration is not None
        assert 0.09 < result.duration < 0.15  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_progress_callback_invoked(self):
        """Test that progress callbacks are invoked correctly."""
        executor = ConcurrentExecutor()
        items = [1, 2, 3]
        callback_invocations = []
        
        async def progress_callback(event_type: str, data: Dict[str, Any]):
            callback_invocations.append((event_type, data))
        
        async def process_item(item, callback):
            await asyncio.sleep(0.01)
            return item * 2
        
        results = await executor.process_files_concurrently(
            items,
            process_item,
            progress_callback=progress_callback
        )
        
        assert len(results) == 3
        assert len(callback_invocations) == 3
        assert all(event == "file_complete" for event, _ in callback_invocations)
    
    @pytest.mark.asyncio
    async def test_synchronous_process_function(self):
        """Test that synchronous process functions work correctly."""
        executor = ConcurrentExecutor()
        items = [1, 2, 3]
        
        def sync_process(item, callback):
            # Synchronous function
            return item * 3
        
        results = await executor.process_files_concurrently(items, sync_process)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.result for r in results] == [3, 6, 9]
    
    @pytest.mark.asyncio
    async def test_kwargs_passed_to_process_function(self):
        """Test that additional kwargs are passed to process function."""
        executor = ConcurrentExecutor()
        items = [1, 2, 3]
        
        async def process_with_kwargs(item, callback, multiplier=1, offset=0):
            return item * multiplier + offset
        
        results = await executor.process_files_concurrently(
            items,
            process_with_kwargs,
            multiplier=5,
            offset=10
        )
        
        assert len(results) == 3
        assert [r.result for r in results] == [15, 20, 25]  # (1*5+10, 2*5+10, 3*5+10)


class TestConcurrentExecutorConcurrency:
    """Tests for concurrency limits and queuing behavior."""
    
    @pytest.mark.asyncio
    async def test_file_concurrency_limit_enforced(self):
        """Test that file concurrency limit is enforced."""
        max_concurrent = 3
        executor = ConcurrentExecutor(max_file_concurrency=max_concurrent)
        items = list(range(10))
        
        max_concurrent_observed = 0
        current_concurrent = 0
        lock = asyncio.Lock()
        
        async def process_item(item, callback):
            nonlocal max_concurrent_observed, current_concurrent
            
            async with lock:
                current_concurrent += 1
                max_concurrent_observed = max(max_concurrent_observed, current_concurrent)
            
            await asyncio.sleep(0.05)  # Simulate work
            
            async with lock:
                current_concurrent -= 1
            
            return item
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 10
        assert all(r.success for r in results)
        assert max_concurrent_observed <= max_concurrent
        assert max_concurrent_observed == max_concurrent  # Should reach the limit
    
    @pytest.mark.asyncio
    async def test_worksheet_concurrency_limit_enforced(self):
        """Test that worksheet concurrency limit is enforced."""
        max_concurrent = 5
        executor = ConcurrentExecutor(max_worksheet_concurrency=max_concurrent)
        items = list(range(15))
        
        max_concurrent_observed = 0
        current_concurrent = 0
        lock = asyncio.Lock()
        
        async def process_item(item, callback):
            nonlocal max_concurrent_observed, current_concurrent
            
            async with lock:
                current_concurrent += 1
                max_concurrent_observed = max(max_concurrent_observed, current_concurrent)
            
            await asyncio.sleep(0.05)  # Simulate work
            
            async with lock:
                current_concurrent -= 1
            
            return item
        
        results = await executor.process_worksheets_concurrently(items, process_item)
        
        assert len(results) == 15
        assert all(r.success for r in results)
        assert max_concurrent_observed <= max_concurrent
        assert max_concurrent_observed == max_concurrent  # Should reach the limit
    
    @pytest.mark.asyncio
    async def test_queuing_when_exceeding_limit(self):
        """Test that operations are queued when exceeding concurrency limit."""
        max_concurrent = 2
        executor = ConcurrentExecutor(max_file_concurrency=max_concurrent)
        items = list(range(6))
        
        processing_order = []
        lock = asyncio.Lock()
        
        async def process_item(item, callback):
            async with lock:
                processing_order.append(("start", item))
            
            await asyncio.sleep(0.1)  # Simulate work
            
            async with lock:
                processing_order.append(("end", item))
            
            return item
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 6
        assert all(r.success for r in results)
        
        # Verify that no more than max_concurrent items were processing at once
        concurrent_count = 0
        max_seen = 0
        for event, item in processing_order:
            if event == "start":
                concurrent_count += 1
                max_seen = max(max_seen, concurrent_count)
            else:
                concurrent_count -= 1
        
        assert max_seen <= max_concurrent
    
    @pytest.mark.asyncio
    async def test_different_concurrency_limits_independent(self):
        """Test that file and worksheet concurrency limits are independent."""
        executor = ConcurrentExecutor(
            max_file_concurrency=2,
            max_worksheet_concurrency=3
        )
        
        file_items = list(range(5))
        worksheet_items = list(range(7))
        
        async def process_file(item, callback):
            await asyncio.sleep(0.05)
            return f"file_{item}"
        
        async def process_worksheet(item, callback):
            await asyncio.sleep(0.05)
            return f"worksheet_{item}"
        
        # Process both concurrently
        file_task = executor.process_files_concurrently(file_items, process_file)
        worksheet_task = executor.process_worksheets_concurrently(worksheet_items, process_worksheet)
        
        file_results, worksheet_results = await asyncio.gather(file_task, worksheet_task)
        
        assert len(file_results) == 5
        assert len(worksheet_results) == 7
        assert all(r.success for r in file_results)
        assert all(r.success for r in worksheet_results)
    
    @pytest.mark.asyncio
    async def test_active_count_returns_to_zero(self):
        """Test that active counts return to zero after processing."""
        executor = ConcurrentExecutor(max_file_concurrency=3)
        items = list(range(10))
        
        async def process_item(item, callback):
            await asyncio.sleep(0.01)
            return item
        
        # Check initial state
        counts_before = executor.get_active_counts()
        assert counts_before["active_files"] == 0
        
        # Process items
        results = await executor.process_files_concurrently(items, process_item)
        
        # Check final state
        counts_after = executor.get_active_counts()
        assert counts_after["active_files"] == 0
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_limit_of_one(self):
        """Test that concurrency limit of 1 processes items sequentially."""
        executor = ConcurrentExecutor(max_file_concurrency=1)
        items = list(range(5))
        
        processing_times = []
        
        async def process_item(item, callback):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.05)
            end = asyncio.get_event_loop().time()
            processing_times.append((start, end))
            return item
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 5
        assert all(r.success for r in results)
        
        # Verify sequential processing: each item should start after the previous one ends
        for i in range(len(processing_times) - 1):
            current_end = processing_times[i][1]
            next_start = processing_times[i + 1][0]
            # Next item should start after or very close to when current item ends
            assert next_start >= current_end - 0.01  # Small tolerance for timing


class TestConcurrentExecutorEdgeCases:
    """Tests for edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_all_items_fail(self):
        """Test behavior when all items fail."""
        executor = ConcurrentExecutor()
        items = [1, 2, 3]
        
        async def failing_process(item, callback):
            raise RuntimeError(f"Failed: {item}")
        
        results = await executor.process_files_concurrently(items, failing_process)
        
        assert len(results) == 3
        assert all(not r.success for r in results)
        assert all(isinstance(r.error, RuntimeError) for r in results)
    
    @pytest.mark.asyncio
    async def test_callback_exception_does_not_break_processing(self):
        """Test that exceptions in callbacks don't break processing."""
        executor = ConcurrentExecutor()
        items = [1, 2, 3]
        
        async def bad_callback(event_type, data):
            raise ValueError("Callback error")
        
        async def process_item(item, callback):
            return item * 2
        
        # Should not raise exception despite bad callback
        results = await executor.process_files_concurrently(
            items,
            process_item,
            progress_callback=bad_callback
        )
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_very_large_item_count(self):
        """Test processing a large number of items."""
        executor = ConcurrentExecutor(max_file_concurrency=10)
        items = list(range(100))
        
        async def process_item(item, callback):
            await asyncio.sleep(0.001)  # Very short delay
            return item
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 100
        assert all(r.success for r in results)
        assert [r.result for r in results] == items
    
    @pytest.mark.asyncio
    async def test_single_item_processing(self):
        """Test processing a single item."""
        executor = ConcurrentExecutor()
        items = [42]
        
        async def process_item(item, callback):
            return item * 2
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 1
        assert results[0].success
        assert results[0].result == 84
    
    @pytest.mark.asyncio
    async def test_none_callback_handling(self):
        """Test that None callback is handled correctly."""
        executor = ConcurrentExecutor()
        items = [1, 2, 3]
        
        async def process_item(item, callback):
            # callback might be None
            return item
        
        results = await executor.process_files_concurrently(
            items,
            process_item,
            progress_callback=None
        )
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_processing_result_attributes(self):
        """Test that ProcessingResult has all expected attributes."""
        executor = ConcurrentExecutor()
        items = [1]
        
        async def process_item(item, callback):
            await asyncio.sleep(0.01)
            return item * 2
        
        results = await executor.process_files_concurrently(items, process_item)
        
        result = results[0]
        assert hasattr(result, 'success')
        assert hasattr(result, 'result')
        assert hasattr(result, 'error')
        assert hasattr(result, 'item')
        assert hasattr(result, 'start_time')
        assert hasattr(result, 'end_time')
        assert hasattr(result, 'duration')
        
        assert result.success is True
        assert result.result == 2
        assert result.error is None
        assert result.item == 1
        assert isinstance(result.start_time, datetime)
        assert isinstance(result.end_time, datetime)
        assert isinstance(result.duration, float)
    
    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self):
        """Test processing with mixed success and failure results."""
        executor = ConcurrentExecutor()
        items = list(range(10))
        
        async def process_item(item, callback):
            if item % 3 == 0:
                raise ValueError(f"Item {item} failed")
            return item * 2
        
        results = await executor.process_files_concurrently(items, process_item)
        
        assert len(results) == 10
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        assert len(successful) == 6  # Items 1,2,4,5,7,8
        assert len(failed) == 4  # Items 0,3,6,9
        
        # Verify failed items
        failed_items = [r.item for r in failed]
        assert set(failed_items) == {0, 3, 6, 9}
