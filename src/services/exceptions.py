class InsufficientDataError(Exception):
    """
    Excepción lanzada cuando el conjunto de datos tras la limpieza
    no cumple con el mínimo requerido para un pronóstico confiable.
    """
    pass
