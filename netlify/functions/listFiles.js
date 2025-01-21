const fs = require('fs');
const path = require('path');

exports.handler = async (event, context) => {
    try {
         //const directoryPath = path.join(process.cwd(), 'posts/');
         const directoryPath = process.cwd();
         const files = fs.readdirSync(directoryPath);

         return {
             statusCode: 200,
             body: JSON.stringify({ files }),
         };
       } catch (error) {
         return {
             statusCode: 500,
             body: JSON.stringify({ 
                error: 'Internal Server Error', 
                message: directoryPath
                yo: error
              }),
         };
     }
};
