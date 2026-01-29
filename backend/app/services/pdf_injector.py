import logging
import io
import pikepdf

logger = logging.getLogger(__name__)

class PDFInjector:
    """
    Service to inject XFA XML data into a PDF template using pikepdf.
    Operations are performed in-memory.
    """

    @staticmethod
    def inject_xml(template_path: str, xml_data: str) -> io.BytesIO:
        """
        Injects the provided XML string into the XFA 'datasets' stream of the PDF template.
        
        Args:
            template_path: Path to the PDF template file.
            xml_data: The XFA XML string to inject.
            
        Returns:
            io.BytesIO: The resulting PDF as a binary stream.
        """
        logger.info(f"Injecting XML into PDF template: {template_path}")
        
        try:
            # Open the template PDF
            with pikepdf.Pdf.open(template_path) as pdf:
                # Ensure xml_data is bytes
                xml_bytes = xml_data.encode('utf-8')
                
                # 1. Try Standard API (pdf.Xfa)
                if hasattr(pdf, 'Xfa'):
                    try:
                        pdf.Xfa['datasets'] = xml_bytes
                        return PDFInjector._save_to_buffer(pdf)
                    except Exception as e:
                        logger.warning(f"Standard pdf.Xfa assignment failed: {e}. Trying manual fallback.")
                
                # 2. Manual Injection Fallback (pdf.Root.AcroForm.XFA)
                try:
                    # Access AcroForm.XFA directly
                    # Note: pikepdf keys might retain the slash in some contexts or require Name objects
                    # We try accessing via attribute which usually works if keys are standard
                    
                    acroform = None
                    if '/AcroForm' in pdf.Root:
                        acroform = pdf.Root['/AcroForm']
                    elif 'AcroForm' in pdf.Root:
                         acroform = pdf.Root['AcroForm']
                    else:
                         # Try attribute access just in case
                         try:
                             acroform = pdf.Root.AcroForm
                         except AttributeError:
                             raise ValueError("No /AcroForm in PDF Root.")

                    xfa_array = None
                    if '/XFA' in acroform:
                        xfa_array = acroform['/XFA']
                    elif 'XFA' in acroform:
                        xfa_array = acroform['XFA']
                    else:
                         try:
                             xfa_array = acroform.XFA
                         except AttributeError:
                            raise ValueError("No /XFA in AcroForm.")
                    
                    # Iterate through XFA array (key, value pairs)
                    injected = False
                    for i in range(0, len(xfa_array), 2):
                        key = xfa_array[i]
                        # key is usually a pikepdf.String, need to cast to str
                        if str(key) == "datasets":
                            # The next item is the stream to replace
                            new_stream = pikepdf.Stream(pdf, xml_bytes)
                            xfa_array[i+1] = new_stream
                            injected = True
                            logger.info("Manually injected XFA datasets via AcroForm array.")
                            break
                    
                    if injected:
                         return PDFInjector._save_to_buffer(pdf)
                    else:
                        logger.warning("XFA found but 'datasets' key missing in manual scan.")
                        raise ValueError("XFA 'datasets' key not found.")
                        
                except Exception as e:
                    # Collect keys for debugging
                    root_keys = list(pdf.Root.keys())
                    raise ValueError(f"Failed to inject XFA. Manual check failed: {e}. Root Keys: {root_keys}")

        except Exception as e:
            logger.error(f"Failed to inject XML into PDF: {e}")
            raise e

    @staticmethod
    def _save_to_buffer(pdf: pikepdf.Pdf) -> io.BytesIO:
        output_buffer = io.BytesIO()
        pdf.save(output_buffer)
        output_buffer.seek(0)
        return output_buffer