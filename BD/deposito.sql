CREATE DATABASE  IF NOT EXISTS `deposito` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `deposito`;
-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: deposito
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `categoria`
--

DROP TABLE IF EXISTS `categoria`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categoria` (
  `id_categoria` int NOT NULL AUTO_INCREMENT,
  `descripcion` varchar(45) NOT NULL,
  PRIMARY KEY (`id_categoria`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `categoria`
--

LOCK TABLES `categoria` WRITE;
/*!40000 ALTER TABLE `categoria` DISABLE KEYS */;
INSERT INTO `categoria` VALUES (1,'Productos'),(2,'Cigarrillos');
/*!40000 ALTER TABLE `categoria` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `factura`
--

DROP TABLE IF EXISTS `factura`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `factura` (
  `id_factura` int NOT NULL AUTO_INCREMENT,
  `fecha` date DEFAULT NULL,
  `nro_telefono` varchar(45) DEFAULT NULL,
  `razon_social` varchar(45) DEFAULT NULL,
  `cliente` varchar(45) DEFAULT NULL,
  `url` varchar(255) DEFAULT NULL,
  `logo` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_factura`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `factura`
--

LOCK TABLES `factura` WRITE;
/*!40000 ALTER TABLE `factura` DISABLE KEYS */;
/*!40000 ALTER TABLE `factura` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `item_factura`
--

DROP TABLE IF EXISTS `item_factura`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `item_factura` (
  `id_item_factura` int NOT NULL AUTO_INCREMENT,
  `id_factura` int NOT NULL,
  `id_producto` int DEFAULT NULL,
  `cantidad` int DEFAULT NULL,
  `precio_unitario` decimal(12,2) DEFAULT NULL,
  PRIMARY KEY (`id_item_factura`,`id_factura`),
  KEY `id_producto_idx` (`id_producto`),
  KEY `id_factura_idx` (`id_factura`),
  CONSTRAINT `id_factura` FOREIGN KEY (`id_factura`) REFERENCES `factura` (`id_factura`),
  CONSTRAINT `id_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `item_factura`
--

LOCK TABLES `item_factura` WRITE;
/*!40000 ALTER TABLE `item_factura` DISABLE KEYS */;
/*!40000 ALTER TABLE `item_factura` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `producto`
--

DROP TABLE IF EXISTS `producto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `producto` (
  `id_producto` int NOT NULL AUTO_INCREMENT,
  `codigo_barra` varchar(45) DEFAULT NULL,
  `descripcion` varchar(100) DEFAULT NULL,
  `costo` decimal(12,2) DEFAULT NULL,
  `ganancia` decimal(5,2) DEFAULT NULL,
  `stock` int DEFAULT '1',
  `tipo_lista` varchar(20) DEFAULT NULL,
  `imprimir` tinyint DEFAULT '1',
  `codigo_proveedor` varchar(45) DEFAULT NULL,
  `fecha_ult_modificacion` date DEFAULT (curdate()),
  `imagen` varchar(255) DEFAULT NULL,
  `id_subcategoria` int DEFAULT NULL,
  PRIMARY KEY (`id_producto`),
  KEY `codigo_barra_idx` (`codigo_barra`) /*!80000 INVISIBLE */,
  KEY `descripcion_idx` (`descripcion`),
  KEY `id_categoria_idx` (`id_subcategoria`),
  CONSTRAINT `id_categoria` FOREIGN KEY (`id_subcategoria`) REFERENCES `subcategoria` (`id_subcategoria`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `producto`
--

LOCK TABLES `producto` WRITE;
/*!40000 ALTER TABLE `producto` DISABLE KEYS */;
INSERT INTO `producto` VALUES (1,NULL,'PILAS ENERGIZER AA',876.65,25.00,1,'M',1,'1147','2026-07-23',NULL,1),(2,NULL,'PILAS ENERGIZER AAA',876.65,25.00,1,'M',1,'1148','2026-07-23',NULL,1),(3,NULL,'PILAS ENERGIZER D2 (GRANDES)',4932.87,25.00,1,'M',1,'1149','2026-07-23',NULL,1),(4,NULL,'PILAS ENERGIZER C2 (MEDIANAS)',3743.14,25.00,1,'M',1,'1150','2026-07-23',NULL,1),(5,NULL,'BATERIA ENERGIZER 9 V',3299.25,25.00,1,'M',1,'1654','2026-07-23',NULL,1),(6,NULL,'PILAS EVEREADY AA',656.23,25.00,1,'M',1,'1151','2026-07-23',NULL,1),(7,NULL,'PILAS EVEREADY AAA',656.23,25.00,1,'M',1,'1155','2026-07-23',NULL,1),(8,NULL,'PILAS EVEREADY D2 (GRANDES)',2338.42,25.00,1,'M',1,'1656','2026-07-23',NULL,1),(9,NULL,'PILAS EVEREADY C2 (MEDIANAS)',1321.93,25.00,1,'M',1,'1652','2026-07-23',NULL,1),(10,NULL,'BATERIA EVEREADY X 9 V',649.45,25.00,1,'M',1,'2015','2026-07-23',NULL,1),(11,NULL,'QUENTO PAPAS (Asado-Crema-BBQ-Clásicas-Jamón s-Ketchup- Limón-Mostaza-Cheddar-Salame)',1648.02,15.00,1,NULL,1,NULL,'2026-07-23',NULL,3),(12,NULL,'QUENTO CONOS, NACHOS, CHIZITOS, BATATAS, MIX',1648.02,15.00,1,NULL,1,NULL,'2026-07-23',NULL,3),(13,NULL,'QUENTO PALITOS',1248.72,15.00,1,NULL,1,NULL,'2026-07-23',NULL,3),(14,NULL,'QUENTO MINI TOSTADAS',1353.26,15.00,1,NULL,1,NULL,'2026-07-23',NULL,3),(15,NULL,'QUENTO ANILLOS x 70 grs.',1396.82,15.00,1,NULL,1,NULL,'2026-07-23',NULL,3),(16,NULL,'QUENTO REDES',943.80,15.00,1,NULL,1,NULL,'2026-07-23',NULL,3),(17,NULL,'QUENTO MANI SABORIZADO',968.05,15.00,1,NULL,1,NULL,'2026-07-23',NULL,3),(18,NULL,'POXIPOL 21 grs.',4281.64,25.00,1,'M',1,'1158','2026-07-23',NULL,4),(19,NULL,'POXILINA x 70 grs.',4271.91,25.00,1,'M',1,'2193','2026-07-23',NULL,4),(20,NULL,'LA GOTITA x 2 ml.',1473.60,25.00,1,'M',1,'1162','2026-07-23',NULL,4),(21,NULL,'LA GOTITA GEL',1849.30,25.00,1,'M',1,'1161','2026-07-23',NULL,4),(22,NULL,'POXI-RAN 23 grs.',2973.64,25.00,1,'M',1,'1155','2026-07-23',NULL,4),(23,NULL,'FASTIX x 25 grs.',3729.22,25.00,1,'M',1,'1159','2026-07-23',NULL,4),(24,NULL,'UNIPOX x 25 grs.',1589.09,25.00,1,'M',1,'1154','2026-07-23',NULL,4),(25,NULL,'EL PULPITO 50 grs.',3936.55,25.00,1,'M',1,'1163','2026-07-23',NULL,4),(26,NULL,'POXITAS x 12 unid.',6087.81,25.00,1,'M',1,'1153','2026-07-23',NULL,4),(27,NULL,'VOLIGOMA x 30 ml.',1092.33,25.00,1,'M',1,'1195','2026-07-23',NULL,4),(28,NULL,'VOLIBARRA x 10 grs.',1433.25,25.00,1,'M',1,'2205','2026-07-23',NULL,4),(29,NULL,'SOLUCION DE GOMA DINI X 5 unid.',4035.35,25.00,1,'M',1,'852','2026-07-23',NULL,4),(30,NULL,'ECCOLE x 9 grs.',4409.66,25.00,1,'M',1,'1156','2026-07-23',NULL,4);
/*!40000 ALTER TABLE `producto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `subcategoria`
--

DROP TABLE IF EXISTS `subcategoria`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subcategoria` (
  `id_subcategoria` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(45) NOT NULL,
  `imprimir` tinyint DEFAULT '1',
  `id_categoria` int DEFAULT NULL,
  PRIMARY KEY (`id_subcategoria`),
  UNIQUE KEY `nombre_UNIQUE` (`nombre`),
  KEY `fk_categoria_idx` (`id_categoria`),
  CONSTRAINT `fk_categoria` FOREIGN KEY (`id_categoria`) REFERENCES `categoria` (`id_categoria`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `subcategoria`
--

LOCK TABLES `subcategoria` WRITE;
/*!40000 ALTER TABLE `subcategoria` DISABLE KEYS */;
INSERT INTO `subcategoria` VALUES (1,'PILAS',1,1),(2,'SNACKS',1,1),(3,'QUENTO',1,1),(4,'SECHI SRL',1,1),(5,'ARTICULOS VARIOS',1,1),(6,'REPELENTES-INSECTICIDAS',1,1),(7,'TRIO',1,1),(8,'GALLETITAS VARIAS',1,1),(9,'RIERA',1,1),(10,'ARROZ',1,1),(11,'NEVARES',1,1),(12,'DAMA',1,1),(13,'ARCOR',1,1),(14,'SEMILLITAS',1,1),(15,'GRABICH',1,1),(16,'CHOCOLATES',1,1),(17,'LHERITIER',1,1),(18,'FANTOCHE',1,1),(19,'MANTECOL',1,1),(20,'MISKY',1,1),(21,'ALFAJORES',1,1),(22,'KINDER',1,1),(23,'BILLIKEN, STANI-ADAMS',1,1),(24,'GOLOSINAS VARIAS',1,1),(25,'ROYAL',1,1),(26,'PASTAS SECAS',1,1),(27,'VINOS-CERVEZAS-GASEOSAS-FERNET',1,1),(28,'JUGOS',1,1),(29,'GALLETITAS Y SNACKS',1,1),(30,'ACEITS',1,1),(31,'MEDICAMENTOS',1,1),(32,'YERBAS',1,1),(33,'ALIMNTOS Y BEBIDAS',1,1),(34,'ENLATADOS',1,1),(35,'GALLETITAS PASEO',1,1),(36,'ALICANTE',1,1),(37,'PRODUCTOS FRACCIONADOS ARTESANALES',1,1),(38,'MASSALIN',1,2),(39,'TODO TABACO',1,2),(40,'BAT',1,2),(41,'SARANDÍ',1,2),(42,'ESPERT',1,2),(43,'TABACALERA DE SANTIAGO',1,2),(44,'TABACOS VARIOS',1,2);
/*!40000 ALTER TABLE `subcategoria` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-23 18:24:34
