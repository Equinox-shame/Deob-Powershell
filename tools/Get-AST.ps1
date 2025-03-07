param (
    # 验证脚本参数，确保它是一个存在的文件并且具有ps1扩展名
    [ValidateScript({
            if(-Not ($_ | Test-Path -PathType Leaf) ){
                throw "ps1 参数必须是一个存在的文件"
            }
            if($_ -notmatch "(\.ps1)"){
                throw "ps1 参数指定的文件必须具有ps1扩展名"
            }
            return $true
        })]
    [Parameter(Mandatory=$true)]
    [System.IO.FileInfo] $ps1,
    [string] $ast,
    [switch] $help
)

$global:n_nodes = 0

# 填充节点函数
function PopulateNode($xmlWriter, $object)
{
    foreach ($child in $object.PSObject.Properties)
    {
        # 跳过父节点
        if ($child.Name -eq 'Parent')
        {
            continue
        }

        $childObject = $child.Value

        # 跳过空值
        if ($null -eq $childObject)
        {
            continue
        }

        # 如果子对象是AST类型，添加子节点
        if ($childObject -is [System.Management.Automation.Language.Ast])
        {
            AddChildNode $xmlWriter $childObject
            continue
        }

        # 如果子对象是AST集合，遍历集合并添加子节点
        $collection = $childObject -as [System.Management.Automation.Language.Ast[]]
        if ($null -ne $collection)
        {
            $xmlWriter.WriteStartElement($child.Name)

            for ($i = 0; $i -lt $collection.Length; $i++)
            {
                AddChildNode $xmlWriter ($collection[$i])
            }

            $xmlWriter.WriteEndElement()
            continue
        }

        # 如果子对象是只读集合，遍历集合并添加子节点
        if ($childObject.GetType().FullName -match 'ReadOnlyCollection.*Tuple`2.*Ast.*Ast')
        {
            for ($i = 0; $i -lt $childObject.Count; $i++)
            {
                AddChildNode $xmlWriter ($childObject[$i].Item1)
                AddChildNode $xmlWriter ($childObject[$i].Item2)
            }
            continue
        }
    }
}

# 添加子节点函数
function AddChildNode($xmlWriter, $child) 
{
    $global:n_nodes += 1

    if ($null -ne $child)
    {
        $xmlWriter.WriteStartElement($child.GetType().Name)

        # 写入属性
        foreach ($property in $child.PSObject.Properties)
        {
            if ($property.Name -in 'Name', 'ArgumentName', 'ParameterName', 'StaticType', 'StringConstantType', 'TypeName', 'VariablePath', 'Operator', 'Variable', 'Condition', 'Static', 'TokenKind', 'Flags')
            {
                $xmlWriter.WriteAttributeString($property.Name, $property.Value);
            }
        }
        # 写入值
        foreach ($property in $child.PSObject.Properties)
        {
            if ($property.Name -in 'Value')
            {
                $xmlWriter.WriteString($property.Value);
            }
        }

        # 递归填充子节点
        PopulateNode $xmlWriter $child

        $xmlWriter.WriteEndElement()
    }
}

# 转换为AST函数
function ConvertToAST($input_filename, $output_filename)
{
    # 解析文件生成AST
    $AST = [System.Management.Automation.Language.Parser]::ParseFile($input_filename, [ref]$null, [ref]$null)

    # 配置XML写入设置
    $xmlsettings = New-Object System.Xml.XmlWriterSettings
    $xmlsettings.Indent = $true
    $xmlsettings.IndentChars = "  "

    # 创建XML写入器
    $XmlWriter = [System.XML.XmlWriter]::Create($output_filename, $xmlsettings)
    if ($null -ne $XmlWriter)
    {
        $xmlWriter.WriteStartDocument()

        # 添加根节点
        AddChildNode $xmlWriter $AST

        $xmlWriter.WriteEndDocument()
        $xmlWriter.Flush()
        $xmlWriter.Close()
    }

        Write-Host $global:n_nodes nodes parsed
    Write-Host (Get-Item $output_filename).length bytes written
}

# 如果未指定ast文件名，生成默认文件名
if ("" -eq $ast)
{
    $ast = [io.path]::ChangeExtension($ps1, '.xml')
}

# 调用转换函数
ConvertToAST $ps1 $ast
