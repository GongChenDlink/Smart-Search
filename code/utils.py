from Cryptodome.Cipher import AES
import base64

class SCrypt(object):
    def __init__(self, key, iv):
        # 密钥key 长度必须为16[AES-128], 24[AES-192], 或者32[AES-256] Bytes
        self.key = key.encode('utf-8')
        # bytes.fromhex(key)
        self.mode = AES.MODE_CBC
        # 向量
        self.iv = iv

    def encrypt(self, text):
        text = text.encode('utf-8')
        cryptor = AES.new(self.key, self.mode, self.iv)

        blockSize = 16
        dataLen = len(text)
        # 与openssl、其他开发语言兼容的填充算法(PKCS7Padding: 块大小在1 ~ 255之间)
        if dataLen < blockSize:
            add = (blockSize - dataLen)
            text = text + bytes([add]) * add
        elif dataLen > blockSize:
            add = (blockSize - (dataLen % blockSize))
            text = text + bytes([add]) * add
        cipher = cryptor.encrypt(text)
        # 因为AES加密时候得到的字符串不一定是ascii字符集的，输出到终端或者保存时候可能存在问题
        # 所以这里统一把加密后的字符串转化为base64
        return str(base64.b64encode(cipher), 'utf-8')

    def decrypt(self, text):
        encry_text = base64.b64decode(text)
        cryptor = AES.new(self.key, self.mode, self.iv)
        plain_text = cryptor.decrypt(encry_text)
        # 去掉填充的16个16
        # return plain_text.rstrip(bytes([16])) # bytes类型
        end = plain_text[len(plain_text) - 1:]
        maybeLen = end[0]
        maybeAppend = plain_text[len(plain_text) - maybeLen:]
        numList = [i for i in maybeAppend]
        fi = list(filter(lambda x: x == end[0], numList))
        # print(fi)
        if len(fi) == len(maybeAppend):
            return str(plain_text.rstrip(end), 'utf-8')
        else:
            return str(plain_text.rstrip(bytes([0])), 'utf-8')
