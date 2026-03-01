"""
Concurrent Executor for parallel processing of files and worksheets.

This module provides semaphore-based concurrency control for translation jobs,
allowing up to 10 files and 10 worksheets to be processed concurrently.
"""

import asyncio
from typing import Callable, List, TypeVar, Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class ProcessingResult:
    """Result of a processing operation."""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    item: Any = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate processing duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class ConcurrentExecutor:
    """
    Manages concurrent execution of file and worksheet processing operations.
    
    Uses semaphores to limit concurrency and implements queuing for operations
    that exceed the configured limits.
    """
    
    def __init__(
        self,
        max_file_concurrency: int = 10,
        max_worksheet_concurrency: int = 10
    ):
        """
        Initialize the concurrent executor.
        
        Args:
            max_file_concurrency: Maximum number of files to process concurrently
            max_worksheet_concurrency: Maximum number of worksheets to process concurrently
        """
        self.max_file_concurrency = max_file_concurrency
        self.max_worksheet_concurrency = max_worksheet_concurrency
        
        # Semaphores for concurrency control
        self._file_semaphore = asyncio.Semaphore(max_file_concurrency)
        self._worksheet_semaphore = asyncio.Semaphore(max_worksheet_concurrency)
        
        # Tracking
        self._active_file_count = 0
        self._active_worksheet_count = 0
        self._file_lock = asyncio.Lock()
        self._worksheet_lock = asyncio.Lock()
        
        logger.info(
            f"ConcurrentExecutor initialized with max_file_concurrency={max_file_concurrency}, "
            f"max_worksheet_concurrency={max_worksheet_concurrency}"
        )
    
    async def process_files_concurrently(
        self,
        items: List[T],
        process_func: Callable[[T, Optional[Callable]], R],
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        **kwargs
    ) -> List[ProcessingResult]:
        """
        Process multiple files concurrently with semaphore-based limiting.
        
        Operations exceeding the concurrency limit are automatically queued
        and processed when capacity becomes available.
        
        Args:
            items: List of items to process (typically file paths)
            process_func: Async function to process each item
            progress_callback: Optional callback for progress updates
            **kwargs: Additional arguments to pass to process_func
            
        Returns:
            List of ProcessingResult objects for each item
        """
        logger.info(f"Starting concurrent file processing for {len(items)} items")
        
        async def _process_with_semaphore(item: T, index: int) -> ProcessingResult:
            """Process a single item with semaphore control."""
            async with self._file_semaphore:
                async with self._file_lock:
                    self._active_file_count += 1
                    active_count = self._active_file_count
                
                logger.debug(
                    f"Processing file {index + 1}/{len(items)} "
                    f"(active: {active_count}/{self.max_file_concurrency})"
                )
                
                start_time = datetime.now()
                result = ProcessingResult(
                    success=False,
                    item=item,
                    start_time=start_time
                )
                
                try:
                    # Call the processing function
                    if asyncio.iscoroutinefunction(process_func):
                        output = await process_func(item, progress_callback, **kwargs)
                    else:
                        output = process_func(item, progress_callback, **kwargs)
                    
                    result.success = True
                    result.result = output
                    logger.debug(f"Successfully processed file {index + 1}/{len(items)}")
                    
                except Exception as e:
                    result.success = False
                    result.error = e
                    logger.error(
                        f"Error processing file {index + 1}/{len(items)}: {str(e)}",
                        exc_info=True
                    )
                
                finally:
                    result.end_time = datetime.now()
                    async with self._file_lock:
                        self._active_file_count -= 1
                    
                    # Send progress update if callback provided
                    if progress_callback:
                        try:
                            await progress_callback(
                                "file_complete",
                                {
                                    "index": index,
                                    "total": len(items),
                                    "success": result.success,
                                    "item": item,
                                    "duration": result.duration
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")
                
                return result
        
        # Create tasks for all items
        tasks = [
            _process_with_semaphore(item, i)
            for i, item in enumerate(items)
        ]
        
        # Execute all tasks concurrently (semaphore handles queuing)
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        logger.info(
            f"File processing complete: {successful} successful, {failed} failed"
        )
        
        return results
    
    async def process_worksheets_concurrently(
        self,
        items: List[T],
        process_func: Callable[[T, Optional[Callable]], R],
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        **kwargs
    ) -> List[ProcessingResult]:
        """
        Process multiple worksheets concurrently with semaphore-based limiting.
        
        Operations exceeding the concurrency limit are automatically queued
        and processed when capacity becomes available.
        
        Args:
            items: List of items to process (typically worksheet objects)
            process_func: Async function to process each item
            progress_callback: Optional callback for progress updates
            **kwargs: Additional arguments to pass to process_func
            
        Returns:
            List of ProcessingResult objects for each item
        """
        logger.info(f"Starting concurrent worksheet processing for {len(items)} items")
        
        async def _process_with_semaphore(item: T, index: int) -> ProcessingResult:
            """Process a single item with semaphore control."""
            async with self._worksheet_semaphore:
                async with self._worksheet_lock:
                    self._active_worksheet_count += 1
                    active_count = self._active_worksheet_count
                
                logger.debug(
                    f"Processing worksheet {index + 1}/{len(items)} "
                    f"(active: {active_count}/{self.max_worksheet_concurrency})"
                )
                
                start_time = datetime.now()
                result = ProcessingResult(
                    success=False,
                    item=item,
                    start_time=start_time
                )
                
                try:
                    # Call the processing function
                    if asyncio.iscoroutinefunction(process_func):
                        output = await process_func(item, progress_callback, **kwargs)
                    else:
                        output = process_func(item, progress_callback, **kwargs)
                    
                    result.success = True
                    result.result = output
                    logger.debug(f"Successfully processed worksheet {index + 1}/{len(items)}")
                    
                except Exception as e:
                    result.success = False
                    result.error = e
                    logger.error(
                        f"Error processing worksheet {index + 1}/{len(items)}: {str(e)}",
                        exc_info=True
                    )
                
                finally:
                    result.end_time = datetime.now()
                    async with self._worksheet_lock:
                        self._active_worksheet_count -= 1
                    
                    # Send progress update if callback provided
                    if progress_callback:
                        try:
                            await progress_callback(
                                "worksheet_complete",
                                {
                                    "index": index,
                                    "total": len(items),
                                    "success": result.success,
                                    "item": item,
                                    "duration": result.duration
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")
                
                return result
        
        # Create tasks for all items
        tasks = [
            _process_with_semaphore(item, i)
            for i, item in enumerate(items)
        ]
        
        # Execute all tasks concurrently (semaphore handles queuing)
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        logger.info(
            f"Worksheet processing complete: {successful} successful, {failed} failed"
        )
        
        return results
    
    def get_active_counts(self) -> Dict[str, int]:
        """
        Get current active processing counts.
        
        Returns:
            Dictionary with active file and worksheet counts
        """
        return {
            "active_files": self._active_file_count,
            "active_worksheets": self._active_worksheet_count,
            "max_files": self.max_file_concurrency,
            "max_worksheets": self.max_worksheet_concurrency
        }
