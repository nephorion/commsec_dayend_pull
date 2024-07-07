class CustomException(Exception):
    def __init__(self, original_exception, new_message):
        self.original_exception = original_exception
        self.new_message = new_message
        super().__init__(self.new_message)

    def __str__(self):
        return f"{self.new_message}: {str(self.original_exception)}"
