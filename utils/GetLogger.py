from datetime import datetime
from functools import wraps
import logging
import pathlib
import inspect
import os
 
 
class GetLogger:
    def __init__(self, log_file_dir, log_file_name, file_handler=False, logger_name=None) -> None:
        if not os.path.exists(log_file_dir):
            pathlib.Path(log_file_dir).mkdir(parents=True, exist_ok=True)
 
        report_time = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
        log_file_path = os.path.join(log_file_dir, f"{report_time}_{log_file_name}")
        formatter = '%(asctime)s - %(levelname)s - %(filename)s.%(funcName)s():%(lineno)s - %(message)s'
        logger_name = logger_name if logger_name else __name__

        if file_handler:
            self.logger = logging.getLogger(logger_name)
            self.handler = logging.FileHandler(log_file_path)
            formatter = logging.Formatter(formatter)
            self.handler.setFormatter(formatter)
            self.logger.addHandler(self.handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False  # Prevent log propagation to root logger

        else:
            logging.basicConfig(
                filename=log_file_path,
                filemode='w',
                format=formatter,
                level=logging.INFO
            )
            self.logger = logging.getLogger(logger_name)
        self.logger.propagate = False  # Prevent log propagation to root logger

def apply_logs_to_all_methods(decorator):
    def class_decorator(cls):
        for attr_name in dir(cls):
            if callable(getattr(cls, attr_name)) and (not attr_name.startswith('__') or attr_name == '__init__'):
                original_attr = getattr(cls, attr_name)
                decorated_attr = decorator(original_attr)
                setattr(cls, attr_name, decorated_attr)
        return cls
    return class_decorator


def log(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        logger = getattr(self, 'logger', None)
        if logger:
            # Get the function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()

            # Create a string of argument names and values
            arg_strs = ", ".join(f"{name}: {value!r}" for name, value in bound_args.arguments.items() if name != 'self')
            log_message = f"{func.__name__} called with ({arg_strs})"
            
            if len(log_message) > 1000:
                log_message = f"{func.__name__} called"
            logger.info(log_message)
        result = func(self, *args, **kwargs)
        return result
    return wrapper
