const ProxyChain = require('proxy-chain');
const port = parseInt(process.argv[2]);
const upstreamProxy = process.argv[3]; // format: http://user:pass@ip:port

const server = new ProxyChain.Server({
    port: port,
    verbose: false,
    native: true, // Use native Node.js features for better performance
    prepareRequestFunction: () => {
        return {
            requestAuthentication: false,
            upstreamProxyUrl: (upstreamProxy === "DIRECT" || !upstreamProxy) ? null : upstreamProxy
        };
    },
});

// Optimization: increase max sockets
require('http').globalAgent.maxSockets = 100;
require('https').globalAgent.maxSockets = 100;

server.listen(() => {
    // console.log(`Proxy listening`);
});