const express = require('express');
const path = require('path');
const app = express();
const port = 8080;

// 设置静态文件目录
app.use(express.static(path.join(__dirname, 'public')));

// 添加根路由处理
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// 错误处理中间件
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send('Something broke!');
});

// 启动服务器
const server = app.listen(port, '0.0.0.0', () => {
    console.log(`Calculator app running at:`);
    console.log(`- Local: http://localhost:${port}`);
    console.log(`- Network: http://${getLocalIP()}:${port}`);
    console.log('Server is listening on all network interfaces');
});

server.on('error', (error) => {
    if (error.code === 'EADDRINUSE') {
        console.error(`Port ${port} is already in use`);
    } else {
        console.error('Server error:', error);
    }
});

// 获取本地IP地址
function getLocalIP() {
    const { networkInterfaces } = require('os');
    const nets = networkInterfaces();
    
    for (const name of Object.keys(nets)) {
        for (const net of nets[name]) {
            // 跳过内部IP和非IPv4地址
            if (net.family === 'IPv4' && !net.internal) {
                return net.address;
            }
        }
    }
    return 'localhost';
}

// 打印所有可用的网络接口
console.log('\nAvailable network interfaces:');
const interfaces = require('os').networkInterfaces();
Object.keys(interfaces).forEach((iface) => {
    interfaces[iface].forEach((details) => {
        if (details.family === 'IPv4') {
            console.log(`${iface}: ${details.address}`);
        }
    });
}); 