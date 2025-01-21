const fs = require('fs');
const path = require('path');

exports.handler = async (event, context) => {
      try {
              const postsDir = path.resolve(__dirname, '../../posts');
              const files = fs.readdirSync(postsDir);

              return {
                        statusCode: 200,
                        body: JSON.stringify({ files }),
                      };
          } catch (error) {
            return {
                      statusCode: 500,
                      body: JSON.stringify({ error: 'Failed to list posts.', message: error}),
                  };
      }
};
