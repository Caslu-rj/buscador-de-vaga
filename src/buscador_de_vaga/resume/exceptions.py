class ResumeReadError(Exception):
    """Exceção base para erros durante a leitura do arquivo de currículo."""


class UnreadablePdfError(ResumeReadError):
    """Lançada quando o PDF possui páginas, mas não contém camada de texto selecionável
    (escaneado/imagem).
    """


class UnsupportedFileFormatError(ResumeReadError):
    """Lançada quando o formato de arquivo não é suportado (diferente de .pdf ou .docx)."""


class EmptyDocumentError(ResumeReadError):
    """Lançada quando o arquivo fornecido está vazio (0 bytes ou sem texto extraível)."""
