import pandas as pd
import os
import re
import zipfile
import unidecode

class MPScraper: 
    
    def request_merge_and_clean_lics(self):

        self._get_csv_from_search()
        self._get_zip_from_mainpage()

        df = self._clean_data()

        return df

