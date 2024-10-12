document.getElementById('uploadButton').addEventListener('click', function() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file) {
        alert('Please choose a file first.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const loading = document.getElementById('loading');
    const originalText = document.getElementById('originalText');
    const cleanedText = document.getElementById('cleanedText');
    loading.style.display = 'block';
    originalText.textContent = '';
    cleanedText.textContent = '';

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loading.style.display = 'none';
        if (data.s3_key) {
            fetch(`/fetch_cleaned_file?s3_key=${data.s3_key}`)
                .then(response => response.text())
                .then(csvText => {
                    const lines = csvText.split('\n');
                    const headers = lines[0].split(',');
                    let originalContent = '';
                    let cleanedContent = '';

                    for (let i = 1; i < lines.length; i++) {
                        if (lines[i].trim()) {
                            const columns = lines[i].split(',');
                            originalContent += columns[0] + '\n';
                            cleanedContent += columns[1] + '\n';
                        }
                    }

                    originalText.textContent = originalContent;
                    cleanedText.textContent = cleanedContent;
                })
                .catch(error => {
                    alert('An error occurred while fetching the cleaned file.');
                    console.error('Error fetching cleaned file:', error);
                });
        } else {
            alert('An error occurred while processing the file.');
            console.error('Error processing file:', data);
        }
    })
    .catch(error => {
        loading.style.display = 'none';
        alert('An error occurred while processing the file.');
        console.error('Error processing file:', error);
    });
});
