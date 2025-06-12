def calculate_columns(container_width, thumb_width, spacing=10):
    return max(1, container_width // (thumb_width + spacing))
