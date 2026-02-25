import wmi
import time
# import queue
import threading
import copy
import pythoncom


'''
通过轮询(用wmi获取信息)，并以分区(vol)的id进行比对，来得出分区挂载和卸载的事件。
（注意：因仅使用分区的id进行比对，故同一分区的驱动器号变更、删除，及其他不改变分区id的操作均无法检测。
请自行根据使用场景进行测试。）
'''


TYPE_BLOCK = 'block'
TYPE_MULTITHREAD = 'multiThread'
EVENT_MOUNT = 1 # 新挂载（出现）
EVENT_UNMOUNT = 0 # 卸载（消失）
DEFAULT_INTERVAL = 2.0 # 单位 秒



class Listener:
    def __init__(self, listenerType: str=TYPE_MULTITHREAD) -> None:
        self.type = listenerType # Monitor 会读取此属性来决定如何call this Listener


    def OnVolumeEvent(self, eventType, volSN, driveObj, timeStamp) -> None:
        pass



class VolumeEventMonitor:
    def __GetVolumes(self) -> list[tuple[str, object]]: # 未完成（内部提供 过滤）
        filter_is_closed = True
        w = wmi.WMI()
        drives = w.Win32_LogicalDisk()
        drivesPack = []
        for drive in drives:
            if (drive.DriveType == 2) or filter_is_closed:  # 3 表示本地磁盘
                drive_info = (drive.VolumeSerialNumber
                            , drive)
                drivesPack.append(drive_info)
                # self.Logger.debug(drive.VolumeSerialNumber)
        return drivesPack


    def __init__(self, checkingInterval:float=DEFAULT_INTERVAL):
        # self.__wmi = wmi.WMI()
        # self.eventsQueue = queue.Queue()
        self.checkingInterval: float = checkingInterval
        self.checkingThread = None
        self.listenersList: list[Listener] = []


    def RegisterListener(self, listenerObj: Listener): # 未完成（检测合法性）
        self.listenersList.append(listenerObj)


    def _CheckingLoop(self) -> None:
        pythoncom.CoInitialize() # 解决多线程BUG
        lastRoundDrivesPack = self.__GetVolumes()
        while True:
            timeStamp: float = time.time()
            eventsList = list()
            drivesPack = self.__GetVolumes()
            SNs: list[str] = [sn for sn,_ in drivesPack]

            lastRoundSNs: list[str] = [sn for sn,_ in lastRoundDrivesPack]

            for volSN, driveObj in drivesPack:
                if volSN not in lastRoundSNs: # 新插入
                    event = (
                        EVENT_MOUNT,
                        volSN,
                        driveObj,
                        timeStamp
                    )
                    #self.eventsQueue.put(event)
                    eventsList.append(event)

            for lastSN, lastDriveObj in lastRoundDrivesPack:
                if lastSN not in SNs: # 拔出
                    event = (
                        EVENT_UNMOUNT,
                        lastSN,
                        lastDriveObj,
                        timeStamp
                    )
                    #self.eventsQueue.put(event)
                    eventsList.append(event)

            lastRoundDrivesPack = drivesPack

            if len(eventsList) > 0:
                self.__CallListeners(eventsList)

            time.sleep(self.checkingInterval)


    def __CallListeners(self, eventsList: list) -> None:
        # 将Listener分类
        multiThreadListenersList: list[Listener] = []
        blockListenersList: list[Listener] = []
        for listenerObj in self.listenersList:
            if listenerObj.type == TYPE_MULTITHREAD:
                multiThreadListenersList.append(listenerObj)
            elif listenerObj.type == TYPE_BLOCK:
                blockListenersList.append(listenerObj)
            else:
                raise

        # 先调起 multiThreadListeners
        for event in eventsList:
            eventType, volSN, driveObj, timeStamp = event
            for mtListener in multiThreadListenersList: # 按顺序
                threading.Thread(
                    target=mtListener.OnVolumeEvent,
                    args=(
                        eventType,
                        volSN,
                        driveObj,
                        timeStamp
                    )
                ).start()

        # 再调起 blockListeners
        for event in eventsList:
            eventType, volSN, driveObj, timeStamp = event
            for bListener in blockListenersList: # 按顺序
                bListener.OnVolumeEvent(eventType, volSN, driveObj, timeStamp)


    def StartCheckingThread(self) -> None: # 已设置 daemon=True # 未完成（错误处理）
        if (self.checkingThread is not None) and self.checkingThread.is_alive():
            raise
        else:
            pass

        self.checkingThread = threading.Thread(
            target=self._CheckingLoop,
            name='VolumeEventCheckingThread',
            daemon=True
        )
        self.checkingThread.start()



if __name__ == '__main__':
    vem = VolumeEventMonitor(checkingInterval=0)
    vem.StartCheckingThread()
    while True:
        try:
            pass
        except KeyboardInterrupt:
            break