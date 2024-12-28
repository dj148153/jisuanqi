let result = document.getElementById('result');

function appendNumber(num) {
    result.value += num;
}

function appendOperator(operator) {
    if (result.value !== '') {
        const lastChar = result.value.slice(-1);
        if ('+-*/%'.includes(lastChar)) {
            result.value = result.value.slice(0, -1) + operator;
        } else {
            result.value += operator;
        }
    }
}

function clearDisplay() {
    result.value = '';
}

function deleteLastChar() {
    result.value = result.value.slice(0, -1);
}

function calculate() {
    try {
        // 替换显示用的乘号为JavaScript运算符
        let expression = result.value.replace('×', '*');
        // 使用eval计算表达式
        result.value = eval(expression);
    } catch (error) {
        result.value = 'Error';
    }
}

// 添加键盘支持
document.addEventListener('keydown', (event) => {
    const key = event.key;
    
    if (/[0-9.]/.test(key)) {
        appendNumber(key);
    } else if (['+', '-', '*', '/', '%'].includes(key)) {
        appendOperator(key);
    } else if (key === 'Enter') {
        calculate();
    } else if (key === 'Backspace') {
        deleteLastChar();
    } else if (key === 'Escape') {
        clearDisplay();
    }
}); 